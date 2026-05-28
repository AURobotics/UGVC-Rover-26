#!/usr/bin/env python3

import math
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy, qos_profile_sensor_data
from geometry_msgs.msg import TwistStamped, PointStamped
from nav_msgs.msg import Odometry, Path
from std_msgs.msg import String


class Pose2D:
    def __init__(self, x=0.0, y=0.0, theta=0.0):
        self.x     = x
        self.y     = y
        self.theta = theta
    
class PurePursuitController:
    def __init__(self, L: float, v: float):
        self.L = L  
        self.v = v 

    def compute(self, pose: Pose2D, lookahead_pt: tuple) -> dict:
        lx, ly = lookahead_pt
        dx = lx - pose.x
        dy = ly - pose.y

        alpha = math.atan2(dy, dx) - pose.theta
        alpha = (alpha + math.pi) % (2 * math.pi) - math.pi

        if abs(alpha) < 0.05:
            omega = 0.0
        else:
            omega = (2.0 * self.v * math.sin(alpha)) / self.L
        max_omega = 0.8 
        omega = max(-max_omega, min(max_omega, omega))

        return {
            "linear": self.v,
            "omega":  omega
        }


def find_lookahead_point(path: list, pose: Pose2D, L: float, last_idx: int = 0):
    min_dist = float('inf')
    closest_idx = last_idx
    
    # search for the nearest point
    for i in range(last_idx, len(path)):
        dist = math.hypot(path[i][0] - pose.x, path[i][1] - pose.y)
        if dist < min_dist:
            min_dist = dist
            closest_idx = i
# find intersection between lookahead circle and path segments
    for i in range(closest_idx, len(path) - 1):
        ax, ay = path[i]
        bx, by = path[i + 1]

        dx_seg = bx - ax
        dy_seg = by - ay
        fx     = ax - pose.x
        fy     = ay - pose.y

        A    = dx_seg**2 + dy_seg**2
        B    = 2 * (fx * dx_seg + fy * dy_seg)
        C    = fx**2 + fy**2 - L**2
        disc = B**2 - 4 * A * C

        if disc < 0 or A < 1e-9:
            continue

        for t in sorted([(-B + math.sqrt(disc)) / (2*A),
                          (-B - math.sqrt(disc)) / (2*A)], reverse=True):
            if 0.0 <= t <= 1.0:
                return (ax + t * dx_seg, ay + t * dy_seg), i

    #fallback --- pick the closest point ahead that satisfies distance L 
    for i in range(closest_idx, len(path)):
        dist = math.hypot(path[i][0] - pose.x, path[i][1] - pose.y)
        if dist >= L:
            return path[i], i

    target_idx = len(path) - 1
    return path[target_idx], target_idx


class ControllerNode(Node):
 
    WAITING      = "WAITING_FOR_PATH"
    GO_TO_START  = "GO_TO_START"     
    NAVIGATING   = "NAVIGATING"
    GOAL_REACHED = "GOAL_REACHED"

    def __init__(self):
        super().__init__("pure_pursuit_node")
        
        self.declare_parameter("lookahead_distance", 1.5)
        self.declare_parameter("desired_velocity",   0.15)
        self.declare_parameter("goal_threshold",     0.15) 

        L           = self.get_parameter("lookahead_distance").value
        v           = self.get_parameter("desired_velocity").value
        self.goal_th = self.get_parameter("goal_threshold").value

        self.controller = PurePursuitController(L=L, v=v)
        
        self.path     = []
        self.path_idx = 0
        self.pose     = Pose2D()
        self.state    = self.WAITING
        self.goal_pt  = None
        
        latch_qos = QoSProfile(
            depth       = 1,
            durability  = DurabilityPolicy.TRANSIENT_LOCAL,
            reliability = ReliabilityPolicy.RELIABLE,
        )

        self.create_subscription(Path, "/controller/path", self._path_callback, latch_qos)
        self.create_subscription(Odometry, "/odom", self._odom_callback, qos_profile_sensor_data)
        self.cmd_pub       = self.create_publisher(TwistStamped, "/cmd_vel", 10)
        self.lookahead_pub = self.create_publisher(PointStamped, "/controller/lookahead", 10)
        self.state_pub     = self.create_publisher(String,       "/controller/fsm_state", 10)

        self.create_timer(0.1, self._control_loop)
        self.get_logger().info("ControllerNode Ready — Waiting for path topic...")

    def _odom_callback(self, msg: Odometry):
        # robpt pose //current
        self.pose.x = msg.pose.pose.position.x
        self.pose.y = msg.pose.pose.position.y
        
        q = msg.pose.pose.orientation
        siny_cosp = 2 * (q.w * q.z + q.x * q.y)
        cosy_cosp = 1 - 2 * (q.y * q.y + q.z * q.z)
        self.pose.theta = math.atan2(siny_cosp, cosy_cosp)

    def _path_callback(self, msg: Path):
        if not msg.poses:
            return
        new_path = [[p.pose.position.x, p.pose.position.y] for p in msg.poses]
        
        if self.state == self.NAVIGATING and self.path:
            self.path = new_path
            self.goal_pt = self.path[-1]
            return

        self.path = new_path
        self.goal_pt = self.path[-1]
        self.path_idx = 0
        
        self.get_logger().info(f"Path loaded ({len(self.path)} pts). Checking proximity to path start...")

        pose = self.pose
        start_pt = self.path[0]
        dist_to_start = math.hypot(start_pt[0] - pose.x, start_pt[1] - pose.y)

        if dist_to_start < 0.2:
            self.state = self.NAVIGATING
            self.get_logger().info("Close to path start. Setting state to NAVIGATING...")
        else:
            self.state = self.GO_TO_START
            self.get_logger().info("Away from path start. Setting state to GO_TO_START...")

    def _control_loop(self):
        self._publish_state()

        if self.state == self.WAITING or not self.path:
            return

        if self.state == self.GOAL_REACHED:
            self._publish_stop()
            return

        pose = self.pose

        if self.state == self.GO_TO_START:
            start_pt = self.path[0]
            dist_to_start = math.hypot(start_pt[0] - pose.x, start_pt[1] - pose.y)

            if dist_to_start > 0.15:
                desired_heading = math.atan2(start_pt[1] - pose.y, start_pt[0] - pose.x)
                heading_error = desired_heading - pose.theta
                heading_error = (heading_error + math.pi) % (2 * math.pi) - math.pi

                if abs(heading_error) < 0.08:
                    self.state = self.NAVIGATING
                    self.get_logger().info("Face aligned with start point! Switching to NAVIGATING...")
                    return 
                else:
                    kp_yaw = 1.8  
                    angular_vel = kp_yaw * heading_error
                    
                    max_ang = 0.5
                    min_ang = 0.15
                    if abs(angular_vel) > max_ang:
                        angular_vel = max_ang if angular_vel > 0 else -max_ang
                    elif abs(angular_vel) < min_ang:
                        angular_vel = min_ang if angular_vel > 0 else -min_ang

                    twist = TwistStamped()
                    twist.header.stamp = self.get_clock().now().to_msg()
                    twist.header.frame_id = "base_link"
                    twist.twist.linear.x  = 0.0
                    twist.twist.angular.z = float(angular_vel)
                    self.cmd_pub.publish(twist)
                    return
            else:
                self.state = self.NAVIGATING
                self.get_logger().info("Already close to start point. Switching to NAVIGATING...")
                return

      
        elif self.state == self.NAVIGATING:
            gx, gy = self.goal_pt
            if math.hypot(gx - pose.x, gy - pose.y) < self.goal_th:
                self.state = self.GOAL_REACHED
                self.get_logger().info("🏁 Goal Reached Successfully!")
                self._publish_stop()
                return
# skip awl 5 points 3shan eel lookahead points t push outside el robot's base
            search_start_idx = max(self.path_idx, 5)

            la_pt, self.path_idx = find_lookahead_point(
                self.path, pose, self.controller.L, search_start_idx
            )

            cmd = self.controller.compute(pose, la_pt)

            twist = TwistStamped()
            twist.header.stamp = self.get_clock().now().to_msg()
            twist.header.frame_id = "base_link"
            twist.twist.linear.x  = float(cmd["linear"])
            twist.twist.angular.z = float(cmd["omega"])
            self.cmd_pub.publish(twist)

            self._publish_lookahead(la_pt)

    def _publish_stop(self):
        twist = TwistStamped()
        twist.header.stamp = self.get_clock().now().to_msg()
        twist.header.frame_id = "base_link"
        twist.twist.linear.x  = 0.0
        twist.twist.angular.z = 0.0
        self.cmd_pub.publish(twist)

    def _publish_state(self):
        msg = String()
        msg.data = self.state
        self.state_pub.publish(msg)

    def _publish_lookahead(self, pt: tuple):  
        msg                 = PointStamped()
        msg.header.frame_id = "odom"
        msg.header.stamp    = self.get_clock().now().to_msg()
        msg.point.x         = float(pt[0])
        msg.point.y         = float(pt[1])
        msg.point.z         = 0.25
        self.lookahead_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = ControllerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()