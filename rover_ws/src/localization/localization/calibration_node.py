import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
from sensor_msgs.msg import MagneticField
from std_srvs.srv import SetBool
from modules.calibration_tools import *

class calibration_node(Node):

    def __init__(self):
        super().__init__('calibration_node')

        self.imu_sub = None
        self.mag_sub = None
        #service to stop collecting data, and calibrate based on the collected data:
        self.imu_cal_srv = self.create_service(SetBool, 'imu_cal', self.imu_calibrate)
        self.mag_cal_srv = self.create_service(SetBool, 'mag_cal', self.mag_calibrate)
        self.F = 30.0 #expected magnetic field is 30micro tesla
        self.mag_data = {
            'x': [],
            'y': [],
            'z': []
        }
        self.gyro_data = {
            'x': [],
            'y': [],
            'z': []
        }
        self.soft_iron = np.array([
            [1,0,0],
            [0,1,0],
            [0,0,1]
        ])
        self.hard_iron = np.array([0,0,0])
        self.collect_data = False
    
    def mag_calibrate(self, request:SetBool.Request, response:SetBool.Response):
        if(request.data == True):
            self.mag_sub = self.create_subscription(
                MagneticField,
                '/phyphox/magnetic_field',
                self.magnet_callback,
                10)
            #clear data incase there were data stored from a previous calibration
            self.mag_data = {
                'x': [],
                'y': [],
                'z': []
            }
            self.collect_data = True
            response.success = True
            response.message = "collecting magnetometer data... set this service to false to get calibration values..."
        else:
            self.destroy_subscription(self.mag_sub)
            self.collect_data = False
            mag_data_list = [self.mag_data['x'], self.mag_data['y'], self.mag_data['z']]
            mag_data_arr = np.array(mag_data_list)
            self.hard_iron, self.soft_iron = get_calib_params(mag_data_arr, self.F)
            response.success = True
            response.message = f'hard iron parameters: {self.hard_iron}\nsoft iron matrix: {self.soft_iron}'
        return response
    
    def imu_calibrate(self, request:SetBool.Request, response:SetBool.Response):
        if(request.data == True):
            self.imu_sub = self.create_subscription(
            Imu,
            '/phyphox/imu',
            self.store_imu_data,
            10)

            #clear data incase there were data stored from a previous calibration
            self.gyro_data = {
                'x': [],
                'y': [],
                'z': []
            }
            response.success = True
            response.message = "collecting IMU data... set this service to false to get calibration values..."
        else:
            self.destroy_subscription(self.imu_sub)
            self.imu_sub = None
            gyro_calibration = [np.mean(self.gyro_data['x']), np.mean(self.gyro_data['y']), np.mean(self.gyro_data['z'])]
            response.success = True
            response.message = gyro_calibration.__str__()
        return response

    def store_imu_data(self, imu:Imu):
        self.gyro_data['x'].append(imu.angular_velocity.x)
        self.gyro_data['y'].append(imu.angular_velocity.y)
        self.gyro_data['z'].append(imu.angular_velocity.z)
    
    def magnet_callback(self, mag:MagneticField):
        x = mag.magnetic_field.x * (10**6) #convert to microtesla
        y = mag.magnetic_field.y * (10**6) 
        z = mag.magnetic_field.z * (10**6) 
        self.mag_data['x'].append(x) 
        self.mag_data['y'].append(y)
        self.mag_data['z'].append(z)




def main(args=None):
    rclpy.init(args=args)

    calibration_node_obj = calibration_node()

    rclpy.spin(calibration_node_obj)

    # Destroy the node explicitly
    # (optional - otherwise it will be done automatically
    # when the garbage collector destroys the node object)
    calibration_node_obj.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
