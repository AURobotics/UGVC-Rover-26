#! /usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Float32MultiArray
from sensor_msgs.msg import NavSatFix, Imu
import random
import math

class TelemetryTestNode(Node):  
    def __init__(self):
        super().__init__('telemetry_test_node')
        self.get_logger().info("Telemetry Test Node Started...")

        self.pub_state = self.create_publisher(String, 'rover/state', 10)
        self.pub_gps = self.create_publisher(NavSatFix, 'rover/gps', 10)
        self.pub_imu = self.create_publisher(Imu, 'rover/imu', 10)
        self.pub_status = self.create_publisher(Float32MultiArray, 'rover/status', 10)

        self.timer = self.create_timer(0.1, self.publish_telemetry)
        self.counter = 0.0

    def publish_telemetry(self): # MN AI
        self.counter += 0.1

        state_msg = String()
        states = ["IDLE", "AUTONOMOUS", "MANUAL", "SCANNING"]
        state_msg.data = random.choice(states)
        self.pub_state.publish(state_msg)


        gps_msg = NavSatFix()
        gps_msg.latitude = 31.2001 + (math.sin(self.counter) * 0.005)
        gps_msg.longitude = 29.9187 + (math.cos(self.counter) * 0.005)
        self.pub_gps.publish(gps_msg)

        imu_msg = Imu()
        imu_msg.linear_acceleration.z = 9.81 + random.uniform(-0.5, 0.5)
        self.pub_imu.publish(imu_msg)

        
        status_msg = Float32MultiArray()
    
        battery_pct = max(0.0, 100.0 - (self.counter * 0.5)) 
        status_msg.data = [
            12.4 + random.uniform(-0.1, 0.1),  
            5.0 + random.uniform(-1.0, 1.0),   
            5.0 + random.uniform(-1.0, 1.0),   
            battery_pct                        
        ]
        self.pub_status.publish(status_msg)

def main(args=None):
    rclpy.init(args=args)
    node = TelemetryTestNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()