import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32
from geometry_msgs.msg import Twist

class PotholePIDNode(Node):
    def __init__(self):
        super().__init__('pothole_pid_node')
        
        # Parameters for runtime tuning
        self.declare_parameter('kp', 3.0)
        self.declare_parameter('ki', 0.0)
        self.declare_parameter('kd', 1.0)
        self.declare_parameter('safe_distance', 1.0) # Target stay 1 meter away
        
        self.current_distance = 5.0
        self.prev_error = 0.0
        self.integral = 0.0
        self.max_integral = 1.0
        self.prev_time = self.get_clock().now()
        
        self.create_subscription(Float32, '/pothole/error', self.error_cb, 10)
        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel/pothole', 10)
        
        self.create_timer(0.05, self.control_loop)
        self.get_logger().info("Pothole PID Node started.")

    def error_cb(self, msg):
        self.current_distance = msg.data

    def control_loop(self):
        kp = self.get_parameter('kp').value
        ki = self.get_parameter('ki').value
        kd = self.get_parameter('kd').value
        safe_dist = self.get_parameter('safe_distance').value
        
        current_time = self.get_clock().now()
        dt = (current_time - self.prev_time).nanoseconds / 1e9
        if dt <= 0.0: return
        
        error = self.current_distance - safe_dist
        
        if error > 2.0:
            # Pothole is far away, output max safe speed (1.38 m/s is ~5 km/h)
            linear_x = 1.38
            self.integral = 0.0 
        else:
            p_term = kp * error
            self.integral = max(min(self.integral + (error * dt), self.max_integral), -self.max_integral)
            i_term = ki * self.integral
            d_term = kd * ((error - self.prev_error) / dt)
            
            linear_x = p_term + i_term + d_term
        
        twist = Twist()

        twist.linear.x = max(min(linear_x, 1.38), 0.0) 
        twist.angular.z = 0.0 
        
        self.cmd_pub.publish(twist)
        
        self.prev_error = error
        self.prev_time = current_time

def main(args=None):
    rclpy.init(args=args)
    node = PotholePIDNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt: 
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()

if __name__ == '__main__':
    main()