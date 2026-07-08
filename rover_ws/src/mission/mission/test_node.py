import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from std_msgs.msg import UInt8
from std_srvs.srv import SetBool

class TestNode(Node):
    def __init__(self):
        super().__init__('test_node')
        
        # 1. Subscriptions & Publishers
        self.state_sub = self.create_subscription(UInt8, '/mission/active_state', self.state_callback, 10)
        self.odom_pub = self.create_publisher(Odometry, '/odom/global', 10)
        
        # 2. Service Servers (Mocking Face Recognition Subsystem)
        self.face_rec_server = self.create_service(SetBool, '/face_recognition/start', self.face_rec_callback)
        
        # 3. Service Clients (To trigger the mission transitions)
        self.toggle_client = self.create_client(SetBool, '/manual_toggle')
        
        # 4. Simulation Control Loop (Runs at 1Hz to step through the environment test)
        self.timer = self.create_timer(1.0, self.test_sequence_loop)
        
        self.step = 0
        self.counter = 0
        self.get_logger().info("====================================================")
        self.get_logger().info("Mission Test Node Started. Waiting for Mission Node...")
        self.get_logger().info("====================================================")

    def state_callback(self, msg: UInt8):
        # Map enum integer values back to labels for clean debugging
        states = {0: "MANUAL", 1: "AUTO_LANES", 2: "AUTO_WAYPOINTS", 3: "AUTO_WAYPOINT2"}
        state_name = states.get(int(msg.data), f"UNKNOWN ({msg.data})")
        self.get_logger().info(f"[MONITOR] Mission Node State -> {state_name}")

    def face_rec_callback(self, request, response):
        self.get_logger().info(f"[MOCK FACE REC] Received service call! Request data: {request.data}")
        response.success = True
        response.message = "Mock Face Recognition node received request successfully."
        return response

    def test_sequence_loop(self):
        self.counter += 1
        
        # --- STEP 0: Wait for nodes to settle, then request Autonomous Mode ---
        if self.step == 0:
            if self.counter >= 3:
                if self.toggle_client.service_is_ready():
                    self.get_logger().info("[TEST SEQUENCE] Requesting switch from MANUAL to AUTO...")
                    req = SetBool.Request()
                    req.data = False  # False triggers AUTO_LANES transition in mission_node
                    self.toggle_client.call_async(req)
                    self.step = 1
                    self.counter = 0
                else:
                    self.get_logger().warn("Waiting for '/manual_toggle' service to be available...")

        # --- STEP 1: Simulate arriving at Waypoint 1 (0.0, 0.0) ---
        elif self.step == 1:
            self.publish_mock_odom(100.0, 100.0)
            if self.counter >= 4:  # Give it 4 seconds to catch the odom frames
                self.get_logger().info("[TEST SEQUENCE] Waypoint 1 hit. Driving toward Waypoint 2...")
                self.step = 2
                self.counter = 0

        # --- STEP 2: Simulate arriving at Waypoint 2 (1.0, 1.0) ---
        elif self.step == 2:
            self.publish_mock_odom(200.0, 200.0)
            if self.counter == 1:
                self.get_logger().info("[TEST SEQUENCE] Waypoint 2 hit. Entering Face Rec Mode.")
                self.get_logger().info("[TEST SEQUENCE] Note: Mission Node will lock here for a 44s timeout.")
            
            # Keep publishing waypoint 2 position until timeout passes
            if self.counter >= 46: 
                self.get_logger().info("[TEST SEQUENCE] Face Recognition timeout should have cleared. Proceeding to Waypoint 3...")
                self.step = 3
                self.counter = 0

        # --- STEP 3: Simulate arriving at Waypoint 3 (2.0, 2.0) ---
        elif self.step == 3:
            self.publish_mock_odom(300.0, 300.0)
            if self.counter >= 5:
                self.get_logger().info("[TEST SEQUENCE] Waypoint 3 hit. Test Sequence Complete.")
                self.timer.cancel()

    def publish_mock_odom(self, x: float, y: float):
        msg = Odometry()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'odom'
        msg.pose.pose.position.x = x
        msg.pose.pose.position.y = y
        self.odom_pub.publish(msg)
        # Log to screen throttled down so it doesn't spam the terminal window
        self.get_logger().info(f"[MOCK ODOM] Transmitting position: x={x}, y={y}", throttle_duration_sec=3.0)

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