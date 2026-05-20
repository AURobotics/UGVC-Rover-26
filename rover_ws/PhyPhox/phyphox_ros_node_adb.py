import rospy
from sensor_msgs.msg import Imu, MagneticField, NavSatFix
from geometry_msgs.msg import Vector3Stamped
from std_msgs.msg import Header
from typing import Optional, Tuple, Dict

# Use the updated Phyphox API client
from phyphox_api_adb import (
    get_all_accelerometer,
    get_all_gyroscope,
    get_all_linear_acceleration,
    get_all_magnetometer,
    get_gps_location,
    start_acquisition,
    stop_acquisition,
    test_connection,
    get_all_sensors,
)


class PhyphoxADBNode:
    
    def __init__(self):
        """Initialize the ROS node"""
        rospy.init_node('phyphox_adb_node', anonymous=False)
        
        # Parameters
        self.base_url = "http://localhost:8080"  # ADB forwarded port
        self.publish_rate = rospy.get_param('~rate', 20.0)  # Hz
        self.frame_id = rospy.get_param('~frame_id', 'phyphox')
        self.timeout = rospy.get_param('~timeout', 2.0)
        
        rospy.loginfo("Phyphox ADB Node Starting...")
        rospy.loginfo(f"Using: {self.base_url} (via ADB port forwarding)")
        
        # ph_api functions handle HTTP; no local session required
        
        # Create publishers
        self.imu_pub = rospy.Publisher('/phyphox/imu', Imu, queue_size=10)
        self.mag_pub = rospy.Publisher('/phyphox/magnetic_field', MagneticField, queue_size=10)
        self.gps_pub = rospy.Publisher('/phyphox/gps', NavSatFix, queue_size=10)
        self.lin_acc_pub = rospy.Publisher('/phyphox/linear_acceleration', Vector3Stamped, queue_size=10)
        
        # Rate limiter
        self.rate = rospy.Rate(self.publish_rate)
        
        # Test connection using ph_api
        if not test_connection():
            rospy.logerr("Failed to connect to Phyphox!")
            rospy.logerr("Make sure:")
            rospy.logerr("  1. Phyphox app is running with Remote Access enabled")
            rospy.logerr("  2. ADB port forwarding is active:")
            rospy.logerr("     adb forward tcp:8080 tcp:8080")
            rospy.signal_shutdown("Connection failed")
            return
            
        rospy.loginfo("✓ Successfully connected to Phyphox!")
        
        # Start acquisition using ph_api
        if start_acquisition():
            rospy.loginfo("✓ Data acquisition started")
        else:
            rospy.logwarn("⚠ Could not start acquisition (may already be running)")
            
    def test_connection(self) -> bool:
        """Test if Phyphox is accessible"""
        # Delegate to ph_api test_connection
        try:
            return test_connection()
        except Exception as e:
            rospy.logerr(f"Connection test failed: {e}")
            return False
            
    def start_acquisition(self) -> bool:
        """Start Phyphox data acquisition"""
        # Kept for compatibility if external callers use the method
        try:
            return start_acquisition()
        except Exception:
            return False
            
    def stop_acquisition(self) -> bool:
        """Stop Phyphox data acquisition"""
        try:
            return stop_acquisition()
        except Exception:
            return False
            
    # Adapter methods that use the updated ph_api functions
    def get_accelerometer(self) -> Optional[Tuple[float, float, float]]:
        """Get accelerometer data (WITH gravity) via ph_api"""
        data = get_all_accelerometer()
        if data:
            return (data.get('x', 0.0), data.get('y', 0.0), data.get('z', 0.0))
        return None

    def get_gyroscope(self) -> Optional[Tuple[float, float, float]]:
        """Get gyroscope data via ph_api"""
        data = get_all_gyroscope()
        if data:
            return (data.get('x', 0.0), data.get('y', 0.0), data.get('z', 0.0))
        return None

    def get_linear_acceleration(self) -> Optional[Tuple[float, float, float]]:
        """Get linear acceleration (WITHOUT gravity) via ph_api"""
        data = get_all_linear_acceleration()
        if data:
            return (data.get('x', 0.0), data.get('y', 0.0), data.get('z', 0.0))
        return None

    def get_magnetic_field(self) -> Optional[Tuple[float, float, float]]:
        """Get magnetometer data via ph_api"""
        data = get_all_magnetometer()
        if data:
            return (data.get('x', 0.0), data.get('y', 0.0), data.get('z', 0.0))
        return None

    def get_gps(self) -> Optional[Dict[str, float]]:
        """Get GPS/location data via ph_api"""
        data = get_gps_location()
        if data:
            # ph_api returns keys like 'lat','lon','altitude' (and more)
            return {
                'latitude': data.get('lat', 0.0),
                'longitude': data.get('lon', 0.0),
                'altitude': data.get('altitude', 0.0),
                'velocity': data.get('velocity', 0.0) if isinstance(data.get('velocity', 0.0), (int, float)) else 0.0,
                'direction': data.get('direction', 0.0) if isinstance(data.get('direction', 0.0), (int, float)) else 0.0,
                'accuracy': data.get('accuracy', 0.0),
                'z_accuracy': data.get('z_accuracy', 0.0),
                'satellites': data.get('satellites', 0.0),
                'status': data.get('status', 0.0),
            }
        return None
        
    def create_header(self) -> Header:
        """Create message header"""
        header = Header()
        header.stamp = rospy.Time.now()
        header.frame_id = self.frame_id
        return header
        
    def publish_imu(self):
        """Publish IMU message (accelerometer WITH gravity + gyroscope)"""
        accel = self.get_accelerometer()
        gyro = self.get_gyroscope()
        
        if accel and gyro:
            msg = Imu()
            msg.header = self.create_header()
            
            # Acceleration (includes gravity - ROS standard)
            msg.linear_acceleration.x = accel[0]
            msg.linear_acceleration.y = accel[1]
            msg.linear_acceleration.z = accel[2]
            
            # Angular velocity
            msg.angular_velocity.x = gyro[0]
            msg.angular_velocity.y = gyro[1]
            msg.angular_velocity.z = gyro[2]
            
            # No orientation estimate
            msg.orientation_covariance[0] = -1
            msg.angular_velocity_covariance[0] = -1
            msg.linear_acceleration_covariance[0] = -1
            
            self.imu_pub.publish(msg)
            
    def publish_magnetic_field(self):
        """Publish magnetometer data"""
        mag = self.get_magnetic_field()
        
        if mag:
            msg = MagneticField()
            msg.header = self.create_header()
            
            # Convert µT to T
            msg.magnetic_field.x = mag[0] * 1e-6
            msg.magnetic_field.y = mag[1] * 1e-6
            msg.magnetic_field.z = mag[2] * 1e-6
            
            msg.magnetic_field_covariance[0] = -1
            
            self.mag_pub.publish(msg)
            
    def publish_gps(self):
        """Publish GPS data using NavSatFix"""
        gps = self.get_gps()
        
        if gps:
            msg = NavSatFix()
            msg.header = self.create_header()
            
            msg.latitude = gps['latitude']
            msg.longitude = gps['longitude']
            msg.altitude = gps['altitude']
            
            msg.status.status = 0  # Fix
            msg.status.service = 1  # GPS
            msg.position_covariance_type = 0  # Unknown
            
            self.gps_pub.publish(msg)
            
    def publish_linear_acceleration(self):
        """Publish linear acceleration (WITHOUT gravity)"""
        lin_acc = self.get_linear_acceleration()
        
        if lin_acc:
            msg = Vector3Stamped()
            msg.header = self.create_header()
            
            msg.vector.x = lin_acc[0]
            msg.vector.y = lin_acc[1]
            msg.vector.z = lin_acc[2]
            
            self.lin_acc_pub.publish(msg)
            
    def spin(self):
        """Main publishing loop"""
        rospy.loginfo(f"Publishing at {self.publish_rate} Hz")
        rospy.loginfo("Press Ctrl+C to stop")
        
        while not rospy.is_shutdown():
            try:
                self.publish_imu()
                self.publish_magnetic_field()
                self.publish_gps()
                self.publish_linear_acceleration()
                
                self.rate.sleep()
                
            except rospy.ROSInterruptException:
                rospy.loginfo("Shutting down...")
                break
            except Exception as e:
                rospy.logerr(f"Error: {e}")
                
        self.stop_acquisition()
        rospy.loginfo("Phyphox ADB node stopped")


def main():
    try:
        node = PhyphoxADBNode()
        node.spin()
    except rospy.ROSInterruptException:
        pass


if __name__ == '__main__':
    main()
