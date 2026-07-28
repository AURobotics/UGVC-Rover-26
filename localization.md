# Table of contents:

1. quick package overview

2. how to calibrate

3. how to simulate

4. how to run (for running on actual hardware)


# quick package overview

## `localization` pacakge main directories:

### launch

* global_launch.py: lauches everything, (global ekf node, navsat transform (gps) node, odom_node and the local launch file)

* local_launch.py: launches global odometry only (sensor fusion, local ekf node, odom_node(kinematic model and magnetometer correction))

* global_launch_sim.py, local_launch_sim.py: same thing but for gazebo simulation. for simulation more nodes are launched and some parameters are slightly different

### localization

* calibration_node.py: used for calibrating magnetometer and gyroscope, the calibration_node has 2 services, one for calibrating the magnetometer(`/mag_cal`) and one for calibrating the gyroscope (`/imu_cal`). calibration details are in the how to calibrate section

* encoder_sim_node.py: used in gazebo simulation to simulate an encoder

* euler_printer: reads `imu/data` and prints angles in degrees for debugging

* odom_node: applies forward kinematics on the wheel velocities, and applies hard iron and soft iron calibration to magnetomer data (the calibration values are output from the calibration node)

* navsat_sim_node: used in gazebo simulation to add covariance values to the GPS data, by default they are set to 0 (bad for localization nodes) which is why this node overrides that value before it is fed to the localization nodes.

### modules

* calibration_tools.py: python module used by calibration node and odom_node to calibrate and correct magnetometer data

### params

* contains configuration parameters for the robot_localization nodes

## imu_filter_madgwick:

* this is a package under the imu_tools directory

* This package is used for sensor fusion between magnetometer and IMU raw data

* the documentation for this node can be found at: https://wiki.ros.org/imu_filter_madgwick

### launch:

* config/imu_filter.yaml: configuration file for the madgwick node. leave the magnetometer bias as zero as the odom_node already handles it

* After imu calibration, this file will be used to set gyro drift (the zeta parameter)

## turtlebot3_gazebo.zip:

* used for simulation, do not unzip because colcon build is not supposed to build this

# How to calibrate:

checkout: https://youtu.be/cGI8mrIanpk?si=u3uapcRKoEspizs1 to learn more about magnetometer calibration, the code from that video is used.

do not forget to source the workspace!

run calibration node

`ros2 run localization calibration_node`

### imu calibration:

while the calibration node is running, call the service with data set to true, this will make the node collect data from the gyroscope for calibration

`ros2 service call /imu_cal std_srvs/srv/SetBool "{data: true}"`

keep imu stationary for a few seconds (5 should be enough) then run

`ros2 service call /imu_cal std_srvs/srv/SetBool "{data: false}"`

this will print the drift of the gyroscope on the screen, go to `imu/tools/imu_filter_madgwick/config/imu_filter.yaml`

set the zeta to the value of the z axis gyroscope drift, (the last element in the array returned by the calibration node)

### magnetometer calibration:

while the calibration node is running, call:

`ros2 service call /mag_cal std_srvs/srv/SetBool "{data: true}"`

rotate the imu for at least 360 degrees slowly (if the imu is installed in the rover, rotate the rover m3lesh)

then call

`ros2 service call /mag_cal std_srvs/srv/SetBool "{data: false}"`

then go to `localization/launch/local_launch.py` and set the soft_iron and hard_iron parameters according to the output of the service

# How to simulate:

### setup:

* follow the turtlebot3 setup tutorial to setup turtlebot3 gazebo simulation: https://emanual.robotis.com/docs/en/platform/turtlebot3/quick-start/#pc-setup

* go to the `src` directory of the turtlebot3 workspace and replace the turtlebot3_gazebo package with the one in the localization pacakge here (after extracting). The zip file is contains a modified version of that package that adds GPS and magnetometer to the simulation

* compile the turtlebot3 workspace

### running:

1. launch gazebo: source the turtlebot3 workspace and in the same terminal run: `export TURTLEBOT3_MODEL=burger; ros2 launch turtlebot3_gazebo empty_world.launch.py`

note that only the burger bot has these modifications

2. launch rviz: source the turtlebot3 workspace and in the same terminal run: `ros2 launch turtlebot3_bringup rviz2.launch.py`

3. launch localization nodes: source the rover workspace and run: `ros2 launch localization global_launch_sim.py`

# How to run

for running the nodes on hardware, just simply source the rover workspace and launch the localization launch file: `ros2 launch localization global_launch.py`

