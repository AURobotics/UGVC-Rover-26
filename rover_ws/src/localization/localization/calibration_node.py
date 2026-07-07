import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
from sensor_msgs.msg import MagneticField
from std_srvs.srv import SetBool
from geometry_msgs.msg import Vector3
# from calibration_tools import *
from scipy import linalg
import numpy as np

class calibration_node(Node):

    def __init__(self):
        super().__init__('calibration_node')

        self.imu_sub = None
        self.mag_sub = self.create_subscription(
            MagneticField,
            '/phyphox/magnetic_field',
            self.magnet_callback,
            10)
        self.publisher_ = self.create_publisher(MagneticField, '/magnetic_field/calibrated', 10)
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
    # def basic_calibration(self):
    #     #find magnetometer bias
    #     max_x = max(self.mag_data['x'])
    #     max_y = max(self.mag_data['y'])
    #     max_z = max(self.mag_data['z'])

    #     min_x = min(self.mag_data['x'])
    #     min_y = min(self.mag_data['y'])
    #     min_z = min(self.mag_data['z'])        
    #     mag_calibration = [ (max_x + min_x) / 2, (max_y + min_y) / 2, (max_z + min_z) / 2]
    #     return mag_calibration
    
    def mag_calibrate(self, request:SetBool.Request, response:SetBool.Response):
        if(request.data == True):
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
            self.collect_data = False
            mag_data_list = [self.mag_data['x'], self.mag_data['y'], self.mag_data['z']]
            mag_data_arr = np.array(mag_data_list)
            M, n, d = self._ellipsoid_fit(mag_data_arr)
            # Calculate calibration parameters
            M_1 = linalg.inv(M)
            self.hard_iron = -np.dot(M_1, n).flatten() #hard iron bias
            self.soft_iron = np.real(self.F / np.sqrt(np.dot(n.T, np.dot(M_1, n)) - d) * linalg.sqrtm(M)) #soft iron
            response.success = True
            response.message = f'hard iron parameters: {self.hard_iron}\nsoft iron matrix: {self.soft_iron}'
        return response
    
    def apply_calibration(self, data):
        # Subtract hard iron bias and apply soft iron correction
        data_corrected = (data - self.hard_iron.T) @ self.soft_iron.T
        return data_corrected
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
            #find gyroscope bias
            # max_x = max(self.gyro_data['x'])
            # max_y = max(self.gyro_data['y'])
            # max_z = max(self.gyro_data['z'])
# 
            # min_x = min(self.gyro_data['x'])
            # min_y = min(self.gyro_data['y'])
            # min_z = min(self.gyro_data['z'])        
            # gyro_calibration = [ (max_x + min_x) / 2, (max_y + min_y) / 2, (max_z + min_z) / 2]
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
        if(self.collect_data == True):
            self.mag_data['x'].append(x) 
            self.mag_data['y'].append(y)
            self.mag_data['z'].append(z)

        #publish calibrated data
        pub_msg = MagneticField()
        pub_msg.header.stamp = self.get_clock().now().to_msg()
        pub_msg.header.frame_id = 'base_link'
        calibrated_field = self.apply_calibration(np.array([x,y,z]))
        pub_msg.magnetic_field.x = calibrated_field[0] * (10**-6) #convert back to tesla
        pub_msg.magnetic_field.y = calibrated_field[1] * (10**-6)
        pub_msg.magnetic_field.z = calibrated_field[2] * (10**-6)
        self.publisher_.publish(pub_msg)

    def _ellipsoid_fit(self, s):
        # D (samples)
        D = np.array([s[0]**2., s[1]**2., s[2]**2.,
                      2.*s[1]*s[2], 2.*s[0]*s[2], 2.*s[0]*s[1],
                      2.*s[0], 2.*s[1], 2.*s[2], np.ones_like(s[0])])

        S = np.dot(D, D.T)
        S_11 = S[:6,:6]
        S_12 = S[:6,6:]
        S_21 = S[6:,:6]
        S_22 = S[6:,6:]

        C = np.array([[-1,  1,  1,  0,  0,  0],
                      [ 1, -1,  1,  0,  0,  0],
                      [ 1,  1, -1,  0,  0,  0],
                      [ 0,  0,  0, -4,  0,  0],
                      [ 0,  0,  0,  0, -4,  0],
                      [ 0,  0,  0,  0,  0, -4]])

        E = np.dot(linalg.inv(C),
                   S_11 - np.dot(S_12, np.dot(linalg.inv(S_22), S_21)))

        E_w, E_v = np.linalg.eig(E)
        v_1 = E_v[:, np.argmax(E_w)]
        if v_1[0] < 0: v_1 = -v_1

        v_2 = np.dot(np.dot(-np.linalg.inv(S_22), S_21), v_1)

        M = np.array([[v_1[0], v_1[5], v_1[4]],
                      [v_1[5], v_1[1], v_1[3]],
                      [v_1[4], v_1[3], v_1[2]]])
        n = np.array([[v_2[0]],
                      [v_2[1]],
                      [v_2[2]]])
        d = v_2[3]

        return M, n, d



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
