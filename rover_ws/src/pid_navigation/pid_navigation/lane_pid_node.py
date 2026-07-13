import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32
from geometry_msgs.msg import Twist

class LanePIDNode(Node):
    def __init__(self):
        super().__init__('lane_pid_node')
        
        # ROS Parameters for runtime tuning
        self.declare_parameter('kp', 3.0)
        self.declare_parameter('ki', 0.0)
        self.declare_parameter('kd', 5)
        self.declare_parameter('base_linear_vel', 1.38) # Forward speed
        self.declare_parameter('max_angular_vel', 1.5)  # Steering limit
        
        self.current_error = 0.0
        self.prev_error = 0.0
        self.integral = 0.0
        self.max_integral = 1.0
        self.prev_time = self.get_clock().now()
        
        self.create_subscription(Float32, '/lane/error', self.error_cb, 10)
        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel/lane', 10)
        
        self.create_timer(0.05, self.control_loop)
        self.get_logger().info("Lane PID Node started.")

    def error_cb(self, msg):
        self.current_error = msg.data

    def control_loop(self):
        # parameters plugged through terminal while running
        #ros2 run pid_navigation lane_pid_node --ros-args -p kp:=<value> -p ki:=<value> -p kd:=<value>
        kp = self.get_parameter('kp').value
        ki = self.get_parameter('ki').value
        kd = self.get_parameter('kd').value
        base_vel = self.get_parameter('base_linear_vel').value
        max_ang = self.get_parameter('max_angular_vel').value
        
        current_time = self.get_clock().now()
        dt = (current_time - self.prev_time).nanoseconds / 1e9
        if dt <= 0.0: return
        
        p_term = kp * self.current_error
        
        self.integral = max(min(self.integral + (self.current_error * dt), self.max_integral), -self.max_integral)
        i_term = ki * self.integral
        
        d_term = kd * ((self.current_error - self.prev_error) / dt)
        
        angular_z = p_term + i_term + d_term
        
        twist = Twist()
        
        twist.linear.x = base_vel 
        twist.angular.z = max(min(angular_z, max_ang), -max_ang) 
        
        self.cmd_pub.publish(twist)
        
        self.prev_error = self.current_error
        self.prev_time = current_time

def main(args=None):
    rclpy.init(args=args)
    node = LanePIDNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt: 
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()

if __name__ == '__main__':
    main()