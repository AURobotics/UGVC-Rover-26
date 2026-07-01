from time import sleep

import adbutils
import adbutils.errors
import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
from rclpy.callback_groups import ReentrantCallbackGroup
from sensor_msgs.msg import Imu, MagneticField, NavSatFix
from geometry_msgs.msg import Vector3Stamped
from std_msgs.msg import Header
from .api.sensor_api import AccelerometerData, GyroscopeData, LinearAccelerationData, LocationData, MagneticFieldData, SensorServer, SensorType


NEEDED_SENSORS = {
    SensorType.ACCELEROMETER,
    SensorType.GYROSCOPE,
    SensorType.LINEAR_ACCELERATION,
    SensorType.MAGNETIC_FIELD,
    SensorType.LOCATION
}

class PhyphoxNode(Node):
    def __init__(self):
        super().__init__('phyphox_node')

        self._adb_client = adbutils.AdbClient()
        self._device: adbutils.AdbDevice | None = None
        self._sensor_server = SensorServer()

        self.declare_parameter('rate', 20.0)  # Hz
        self.declare_parameter('frame_id', 'phyphox')
        self.declare_parameter('timeout', 0.1)

        self.publish_rate = self.get_parameter('rate').get_parameter_value().double_value
        self.frame_id = self.get_parameter('frame_id').get_parameter_value().string_value
        self.timeout = self.get_parameter('timeout').get_parameter_value().double_value
        
        self.get_logger().info("PhyPhox ADB Node Starting...")
        
        self.imu_pub = self.create_publisher(Imu, '/phyphox/imu', 10)
        self.mag_pub = self.create_publisher(MagneticField, '/phyphox/magnetic_field', 10)
        self.gps_pub = self.create_publisher(NavSatFix, '/phyphox/gps', 10)
        self.lin_acc_pub = self.create_publisher(Vector3Stamped, '/phyphox/linear_acceleration', 10)

        self.connect_device()
        self.start_acquisition()

        timer_period = 1.0 / self.publish_rate
        self.callback_group = ReentrantCallbackGroup()
        self._publish_timer = self.create_timer(timer_period, self._publish_callback, callback_group=self.callback_group)
        self._vitals_timer = self.create_timer(5, self._vitals_callback, callback_group=self.callback_group)
        self.get_logger().info(f'Publishing at {self.publish_rate} Hz')
            
    @property
    def device_connected(self) -> bool:
        if self._device is None:
            return False
        try:
            return self._device.get_state() == 'device'
        except adbutils.errors.AdbError:
            return False
        
    def connect_device(self) -> None:
        """Connects to first adb device if present and is currently not connected"""
        if self.device_connected:
            return
        self.get_logger().info('Attempting to connect to ADB device...')
        devices = self._adb_client.device_list()
        if not devices:
            self._device = None
            self.get_logger().warn('No ADB devices found')
            return
        self._device = devices[0]
        port = self._device.forward_port('tcp:8080') # TODO: use parameter file here?
        self._sensor_server.port = port
        self.get_logger().info(f'Connected to ADB device: {self._device.serial}')
        self.get_logger().info(f'Forwarded PhyPhox port tcp:8080 to tcp:{port}')
        
    def disconnect_device(self) -> None:
        try:
            if self._device:
                self._sensor_server.stop_acquisition()
                self._device.forward_remove_all()
                self._device = None
        except:
            pass
        self.get_logger().warn('ADB device disconnected')

    def start_acquisition(self) -> None:
        self.get_logger().info('Starting sensor data acqusition...')
        if not self._sensor_server.server_alive:
            self.get_logger().warn('Failed to connect to PhyPhox experiment server')
            return
        
        sensors = self._sensor_server.sensors
        if not NEEDED_SENSORS.issubset(sensors):
            self.get_logger().warn(f'PhyPhox experiment is missing sensor(s): {NEEDED_SENSORS.difference(sensors)}')
            return
        
        self._sensor_server.start_acquisition()
        sleep(0.5)
        if not self._sensor_server.acquisition_is_on:
            self.get_logger().warn('Data acquisition failed to start')

    def stop_acquisition(self) -> None:
        self.get_logger().info('Stopping sensor data acqusition...')
        if not self._sensor_server.server_alive:
            return
        self._sensor_server.stop_acquisition()
        
    def create_header(self) -> Header:
        """Create message header"""
        header = Header()
        header.stamp = self.get_clock().now().to_msg()
        header.frame_id = self.frame_id
        return header
        
    def _publish_callback(self):
        if not self.context.ok():
            return
            
        try:
            all_data = self._sensor_server.get_sensors_data(list(NEEDED_SENSORS))
            if self.context.ok():
                self.publish_imu(all_data.get(SensorType.ACCELEROMETER), all_data.get(SensorType.GYROSCOPE))
                self.publish_magnetic_field(all_data.get(SensorType.MAGNETIC_FIELD))
                self.publish_gps(all_data.get(SensorType.LOCATION))
                self.publish_linear_acceleration(all_data.get(SensorType.LINEAR_ACCELERATION))
            
        except Exception as e:
            if self.context.ok():
                self.get_logger().error(f"Error in timer callback: {e}")

    def publish_imu(self, accel: AccelerometerData | None, gyro: GyroscopeData | None):
        """Publish IMU message (accelerometer WITH gravity + gyroscope)"""
        if accel and gyro:
            msg = Imu()
            msg.header = self.create_header()
            
            msg.linear_acceleration.x = accel.accX
            msg.linear_acceleration.y = accel.accY
            msg.linear_acceleration.z = accel.accZ
            
            msg.angular_velocity.x = gyro.gyrX
            msg.angular_velocity.y = gyro.gyrY
            msg.angular_velocity.z = gyro.gyrZ
            
            # No orientation estimate
            msg.orientation_covariance[0] = -1.0
            msg.angular_velocity_covariance[0] = -1.0
            msg.linear_acceleration_covariance[0] = -1.0
            
            self.imu_pub.publish(msg)
            
    def publish_magnetic_field(self, mag: MagneticFieldData | None):
        if mag:
            msg = MagneticField()
            msg.header = self.create_header()
            
            # Convert µT to T
            msg.magnetic_field.x = mag.magX * 1e-6
            msg.magnetic_field.y = mag.magY * 1e-6
            msg.magnetic_field.z = mag.magZ * 1e-6
            
            msg.magnetic_field_covariance[0] = -1.0
            
            self.mag_pub.publish(msg)
            
    def publish_gps(self, gps: LocationData | None):
        """Publish GPS data using NavSatFix"""
        if gps:
            msg = NavSatFix()
            msg.header = self.create_header()
            
            msg.latitude = gps.locLat
            msg.longitude = gps.locLon
            msg.altitude = gps.locZ
            
            msg.status.status = 0
            msg.status.service = 1
            msg.position_covariance_type = NavSatFix.COVARIANCE_TYPE_UNKNOWN
            
            self.gps_pub.publish(msg)
            
    def publish_linear_acceleration(self, lin_acc: LinearAccelerationData | None):
        """Publish linear acceleration (WITHOUT gravity)"""
        if lin_acc:
            msg = Vector3Stamped()
            msg.header = self.create_header()
            
            msg.vector.x = lin_acc.linX
            msg.vector.y = lin_acc.linY
            msg.vector.z = lin_acc.linZ
            
            self.lin_acc_pub.publish(msg)

    def _vitals_callback(self) -> None:
        if not self.device_connected:
            self.connect_device()
        if not self._sensor_server.server_alive or not self._sensor_server.acquisition_is_on:
            self.start_acquisition()


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = PhyphoxNode()
        executor = MultiThreadedExecutor()
        executor.add_node(node)
        executor.spin()
    except (KeyboardInterrupt, RuntimeError):
        print("\nTerminating node interface...")
    finally:
        if node is not None:
            node._publish_timer.cancel()
            node._vitals_timer.cancel()
            
            try:
                node.disconnect_device()
            except Exception:
                pass
            
            node.destroy_node()
        try:
            if rclpy.ok():
                rclpy.shutdown()
        except Exception:
            pass


if __name__ == '__main__':
    main()