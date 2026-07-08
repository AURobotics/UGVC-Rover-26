# Table of contents:

1. quick package overview

2. how to calibrate

3. how to simulate

3. how to run (in the trial and for testing on hardware)


# quick package overview

## `localization` pacakge main directories:

### launch

* global_launch.py: lauches everything, (local ekf node, global ekf node, navsat transform (gps) node, sensor fusion node, odom_node (kinematic model and magnetometer correction))

* local_launch.py: launches global odometry only (sensor fusion, local ekf node, odom_node(kinematic model and magnetometer correction))

* global_launch_sim.py, local_launch_sim.py: same thing but for gazebo simulation

### localization

* calibration_node.py: used for calibrating magnetometer and gyroscope, the calibration_node has 2 services, one for calibrating the magnetometer(`/mag_cal`) and one for calibrating the gyroscope (`/imu_cal`). calibration details are in the how to use section

* encoder_sim_node.py: used in gazebo simulation to simulate an encoder

* euler_printer: reads `imu/data` and prints angles in degrees for debugging

* odom_node: applies forward kinematics on the wheel velocities, and applies hard iron and soft iron calibration (the calibration values are output from the calibration node) on magnetomer data

### modules

* calibration_tools.py: python module used by calibration node and odom_node to calibrate and correct magnetometer data

### params

* contains configuration parameters for the robot_localization nodes

## imu_filter_madgwick:

* this is a package under the imu_tools directory, the documentation for this node can be found at: https://wiki.ros.org/imu_filter_madgwick

### launch:

* config/imu_filter.yaml: DO NOT MESS WITH MAGNETOMETER BIAS, THIS IS HANDLED BY THE ODOM NODE, but after imu calibration, this file will be used to set gyro drift (the zeta parameter)

## turtlebot3_gazebo.zip:

* used for simulation, do not unzip because colcon build is not supposed to build this

# How to calibrate:

do not forget to source the workspace

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

ok I am tired I will continue later
