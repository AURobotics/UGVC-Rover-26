#!/usr/bin/env python3
# server node for generating Bezier paths and controlling the robot via FSM commands
import math
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer, GoalResponse, CancelResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy

from geometry_msgs.msg import PoseStamped, Twist, TwistStamped
from nav_msgs.msg import Path, Odometry
from std_msgs.msg import Bool   #fsm emergency stop signal
from visualization_msgs.msg import Marker, MarkerArray 

from rover_interfaces.action import GenerateBezierPath

EARTH_RADIUS_M = 6_371_000.0


def gps_to_xy(lat, lon, origin_lat, origin_lon):
    x = math.radians(lon - origin_lon) * math.cos(math.radians(origin_lat)) * EARTH_RADIUS_M
    y = math.radians(lat - origin_lat) * EARTH_RADIUS_M
    return np.array([x, y])


def yaw_to_quaternion(yaw):
    return (0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0))


def quaternion_to_yaw(orientation):
    x, y, z, w = orientation.x, orientation.y, orientation.z, orientation.w
    siny_cosp = 2.0 * (w * z + x * y)
    cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
    return math.atan2(siny_cosp, cosy_cosp)


class BezierCurve:
    def __init__(self, control_scale=0.3, min_control_dist=0.2, points_per_meter=15):
        self.control_scale    = control_scale
        self.min_control_dist = min_control_dist
        self.points_per_meter = points_per_meter

    def generate(self, P0, theta0, P3, theta3) -> np.ndarray:
        P0 = np.array(P0, dtype=float)
        P3 = np.array(P3, dtype=float)
        path_length  = np.linalg.norm(P3 - P0)
        control_dist = max(self.min_control_dist, self.control_scale * path_length)

        P1 = P0 + control_dist * np.array([math.cos(theta0), math.sin(theta0)])
        P2 = P3 - control_dist * np.array([math.cos(theta3), math.sin(theta3)])

        num_points = max(10, int(self.points_per_meter * path_length))
        t = np.linspace(0, 1, num_points).reshape(-1, 1)

        trajectory = ((1 - t)**3        * P0 +
                      3*(1 - t)**2 * t   * P1 +
                      3*(1 - t)   * t**2 * P2 +
                      t**3               * P3)
        return trajectory

    def heading_between2p(self, A, B) -> float:
        return math.atan2(B[1] - A[1], B[0] - A[0])

    def compute_headings(self, pts: list) -> list:
        n = len(pts)
        headings = []
        for i in range(n):
            if i == 0:
                h = self.heading_between2p(pts[0], pts[1])
            elif i == n - 1:
                h = self.heading_between2p(pts[-2], pts[-1])
            else:
                h_in  = self.heading_between2p(pts[i - 1], pts[i])
                h_out = self.heading_between2p(pts[i],     pts[i + 1])
                h = math.atan2(math.sin(h_in) + math.sin(h_out), math.cos(h_in) + math.cos(h_out))
            headings.append(h)
        return headings

    def build_leg_segments(self, xy_waypoints: list) -> list:
        pts = [np.array(p, dtype=float) for p in xy_waypoints]
        n = len(pts)
        if n < 2:
            raise ValueError("Need at least 2 waypoints")

        headings = self.compute_headings(pts)
        segments = []
        for i in range(n - 1):
            seg = self.generate(P0=pts[i], theta0=headings[i], P3=pts[i + 1], theta3=headings[i + 1])
            segments.append(seg)
        return segments, headings


class BezierPathServer(Node):
    def __init__(self):
        super().__init__("bezier_path_server")
        self.cb_group = ReentrantCallbackGroup()

       # parameters for controller
        self.declare_parameter("control_scale",    0.3)
        self.declare_parameter("min_control_dist", 0.2)
        self.declare_parameter("points_per_meter", 15)
        self.declare_parameter("lookahead_dist",   0.6)  
        self.declare_parameter("linear_velocity",  0.3)  

        self.generator = BezierCurve(
            control_scale    = self.get_parameter("control_scale").value,
            min_control_dist = self.get_parameter("min_control_dist").value,
            points_per_meter = int(self.get_parameter("points_per_meter").value)
        )
        self.Ld = self.get_parameter("lookahead_dist").value
        self.v_target = self.get_parameter("linear_velocity").value

        # internal state variables
        self.current_path_nodes = []  
        self.robot_x = 0.0
        self.robot_y = 0.0
        self.robot_yaw = 0.0
        self.controller_active = False
        self.emergency_stop_triggered = False # fsm emergency stop flag

        
        latch_qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL, reliability=ReliabilityPolicy.RELIABLE)
        self.dense_path_pub = self.create_publisher(Path, "/controller/dense_path", latch_qos)
        self.cmd_vel_pub = self.create_publisher(TwistStamped, "/cmd_vel", 10)
        self.marker_pub = self.create_publisher(MarkerArray, "/controller/waypoint_markers", latch_qos)
        self.odom_sub = self.create_subscription(Odometry, "/odom", self._odom_callback, 10, callback_group=self.cb_group)
        self.estop_sub = self.create_subscription(Bool, "/fsm/emergency_stop", self._emergency_stop_callback, 10, callback_group=self.cb_group)

        self._action_server = ActionServer(
            self, GenerateBezierPath, 'generate_bezier_path',
            execute_callback=self._execute_callback,
            goal_callback=self._goal_callback,
            cancel_callback=self._cancel_callback,
            callback_group=self.cb_group
        )

        # timer 20hz 
        self.control_timer = self.create_timer(0.05, self._control_loop_callback, callback_group=self.cb_group)
        self.get_logger().info(" Bezier Server + FSM Controller Node initialized and ready to accept goals")

    def _odom_callback(self, msg):
        self.robot_x = msg.pose.pose.position.x
        self.robot_y = msg.pose.pose.position.y
        self.robot_yaw = quaternion_to_yaw(msg.pose.pose.orientation)

    def _emergency_stop_callback(self, msg): #fsm emergency stop signal
       
        if msg.data:
            self.get_logger().error("EMERGENCY STOP command received from FSM")
            self.emergency_stop_triggered = True
            self.controller_active = False
            self._stop_robot()

    def _goal_callback(self, goal_request):
        self.get_logger().info("FSM requested a new Bezier Path execution.")
        if len(goal_request.raw_gps_path.poses) < 2:
            self.get_logger().warn("Rejected Goal: Empty or single waypoint.")
            return GoalResponse.REJECT
        self.emergency_stop_triggered = False 
        return GoalResponse.ACCEPT

    def _cancel_callback(self, goal_handle):
        self.get_logger().info("FSM requested to CANCEL the current goal.")
        self.controller_active = False
        self._stop_robot()
        return CancelResponse.ACCEPT

    def _stop_robot(self):
        stop_msg = TwistStamped()
        stop_msg.header.stamp = self.get_clock().now().to_msg()
        stop_msg.header.frame_id = "base_link"
        self.cmd_vel_pub.publish(stop_msg)

    def _execute_callback(self, goal_handle):
    
        feedback_msg = GenerateBezierPath.Feedback()
        result = GenerateBezierPath.Result()

        self.controller_active = False
        self.current_path_nodes = []

        raw_gps_poses = goal_handle.request.raw_gps_path.poses
        origin_lat = raw_gps_poses[0].pose.position.x
        origin_lon = raw_gps_poses[0].pose.position.y

        meter_waypoints = []
        for p in raw_gps_poses:
            xy = gps_to_xy(p.pose.position.x, p.pose.position.y, origin_lat, origin_lon)
            meter_waypoints.append(xy.tolist())

        try:
            leg_segments, headings = self.generator.build_leg_segments(meter_waypoints)
            path_msg = Path()
            path_msg.header.frame_id = "odom"
            path_msg.header.stamp = self.get_clock().now().to_msg()

            temp_path_nodes = []
            for leg_idx, seg in enumerate(leg_segments):
                theta_start = headings[leg_idx]
                theta_end   = headings[leg_idx + 1]

                for j, (x, y) in enumerate(seg):
                    temp_path_nodes.append([x, y])
                    
                    ps = PoseStamped()
                    ps.header = path_msg.header
                    ps.pose.position.x = float(x)
                    ps.pose.position.y = float(y)
                    ps.pose.position.z = 0.0

                    frac = j / max(1, len(seg) - 1)
                    yaw = theta_start + frac * (theta_end - theta_start)
                    qx, qy, qz, qw = yaw_to_quaternion(yaw)
                    ps.pose.orientation.x = qx
                    ps.pose.orientation.y = qy
                    ps.pose.orientation.z = qz
                    ps.pose.orientation.w = qw
                    path_msg.poses.append(ps)

            # نشر المسار الكثيف في الـ Network للـ RViz وباقي النودز
            self.dense_path_pub.publish(path_msg)
            self.current_path_nodes = temp_path_nodes
            # 🔵 رسم الـ Waypoints الـ 4 الأساسية كـ كرات واضحة في RViz
            marker_array = MarkerArray()
            for idx, wp in enumerate(meter_waypoints):
                marker = Marker()
                marker.header = path_msg.header
                marker.ns = "waypoints"
                marker.id = idx
                marker.type = Marker.SPHERE # شكل كورة
                marker.action = Marker.ADD
                
                # الإحداثيات بالأمتار
                marker.pose.position.x = float(wp[0])
                marker.pose.position.y = float(wp[1])
                marker.pose.position.z = 0.1 # مرتفعة قليلاً عن الأرض عشان تبان
                
                # حجم الكورة (نص متر مثلاً عشان تبان من بعيد)
                marker.scale.x = 0.5
                marker.scale.y = 0.5
                marker.scale.z = 0.5
                
                # لون الكورة (أزرق فاقع)
                marker.color.r = 0.0
                marker.color.g = 0.0
                marker.color.b = 1.0
                marker.color.a = 1.0 # الشفافية (ظاهرة بالكامل)
                
                marker_array.markers.append(marker)
            
            self.marker_pub.publish(marker_array) # نشر النقط
            # لو الطوارئ اشتغلت أثناء الحسابات، اخرج فورًا
            if self.emergency_stop_triggered:
                goal_handle.abort()
                result.success = False
                result.message = "Aborted due to pre-execution Emergency Stop."
                return result

            self.controller_active = True
            self.get_logger().info(f"Trajectory computed successfully ({len(temp_path_nodes)} pts). Tracking initiated! 🚀")

            # ⏳ إنشاء ROS Rate آمن للـ Multi-threading (بمعدل 2 هرتز لإرسال الـ Feedback)
            loop_rate = self.create_rate(2.0)

            # اللوب دي بتفضل شغالة طول ما الروبوت بيتحرك وبتغذي الـ FSM بالـ Feedback
            while self.controller_active and rclpy.ok():
                if not goal_handle.is_active:
                    self._stop_robot()
                    return result
                
                # إرسال الـ Feedback الحالي للـ FSM Client المتابع بره
                feedback_msg.status = f"Tracking Bezier... Robot at: X={self.robot_x:.2f}, Y={self.robot_y:.2f}"
                goal_handle.publish_feedback(feedback_msg)
                
                loop_rate.sleep()

            # تشيك أخير بعد الخروج من الـ Loop لمعرفة سبب الوقوف
            if self.emergency_stop_triggered:
                self.get_logger().error("Goal aborted internally due to E-Stop.")
                goal_handle.abort()
                result.success = False
                result.message = "Execution aborted by FSM Emergency Stop."
                return result

            if goal_handle.is_active:
                goal_handle.succeed()
                
            result.success = True
            result.total_generated_points = len(temp_path_nodes)
            result.message = "FSM Update: Rover reached the final GPS waypoint successfully!"
            return result

        except Exception as e:
            self.get_logger().error(f"Execution failed: {str(e)}")
            self.controller_active = False
            self._stop_robot()
            if goal_handle.is_active:
                goal_handle.abort()
            result.success = False
            result.message = f"Internal server error: {str(e)}"
            return result

    def _control_loop_callback(self):
        """خوارزمية الـ Pure Pursuit لتوجيه الـ Rover بدقة على المنحنى"""
        if not self.controller_active or not self.current_path_nodes or self.emergency_stop_triggered:
            return

        # 1. حساب المسافة المتبقية حتى آخر نقطة في المنحنى كله (الـ Goal الحقيقي)
        min_dist_to_goal = math.hypot(self.current_path_nodes[-1][0] - self.robot_x, self.current_path_nodes[-1][1] - self.robot_y)

        # إذا وصلنا في حدود نطاق السماح (25 سم) نوقف الروبوت وننهي الحركة بنجاح
        if min_dist_to_goal < 0.25:
            self.get_logger().info("🎯 Goal target region achieved. Stopping controller loop.")
            self.controller_active = False
            self._stop_robot()
            return

        # 2. البحث عن الـ Lookahead Point المناسبة بناءً على مسافة الـ Ld
        target_pt = None
        for pt in reversed(self.current_path_nodes):
            dist = math.hypot(pt[0] - self.robot_x, pt[1] - self.robot_y)
            if dist <= self.Ld:
                target_pt = pt
                break

        if target_pt is None:
            target_pt = self.current_path_nodes[-1]

        # 3. حساب زاوية الخطأ (Alpha) بين مقدمة الروبوت والنقطة المستهدفة
        goal_heading = math.atan2(target_pt[1] - self.robot_y, target_pt[0] - self.robot_x)
        alpha = goal_heading - self.robot_yaw
        alpha = math.atan2(math.sin(alpha), math.cos(alpha)) # حصر الزاوية بين [-PI, PI]

        # 4. حساب السرعة الدورانية (Omega) بمعادلة الـ Pure Pursuit الهندسية
        angular_vel = (2.0 * self.v_target * math.sin(alpha)) / self.Ld

        # 5. نشر السرعات على توبيك الـ المحاكاة والمواتير
     # 5. نشر السرعات بنوع TwistStamped للمحاكاة
        cmd_msg = TwistStamped()
        cmd_msg.header.stamp = self.get_clock().now().to_msg()
        cmd_msg.header.frame_id = "base_link" # أو اسم الفريم بتاع الروبوت عندك
        
        # وضع السرعات جوه الـ twist sub-message
        cmd_msg.twist.linear.x = self.v_target
        cmd_msg.twist.angular.z = angular_vel
        
        self.cmd_vel_pub.publish(cmd_msg)

def main(args=None):
    rclpy.init(args=args)
    node = BezierPathServer()
    from rclpy.executors import MultiThreadedExecutor
    executor = MultiThreadedExecutor()
    rclpy.spin(node, executor=executor)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()