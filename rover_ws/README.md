# Overview:
* `rover_ws/src/localization`: contains launch files and configuration files for the `robot_localization` nodes as well as the odom node (the node that takes encoders output and outputs /odometry/unfiltered)

* `rover_ws/src/simulation_localization`: contains the fake encoders node, which uses the positional data of the wheels in turtlebot3 as encoder data (use only for simultion)

* `rover_ws/turtlebot3_gazebo`: contains a modified version of the gazebo simulation package of the turtlebot3 simulation repo (more details later)

# How to simulate?
* if you do not have turtlebot3 repo already setup, follow the setup instructions: https://emanual.robotis.com/docs/en/platform/turtlebot3/quick-start/#pc-setup

* navigate to `turtlebot3_ws/src/turtlebot3_simulations` and replace the `turtlebot3_gazebo` directory with the modified one I included in `rover_ws/`

* now you can run the following commands (do not forget to build both the turtbot3 packages, and the rover_ws packages first)

start gazebo simulation(make sure you are in the parent directory of turtlebot3\_ws): `export TURTLEBOT3_MODEL=burger; source turtlebot3_ws/install/setup.bash; ros2 launch turtlebot3_gazebo empty_world.launch.py`

start rviz: `source turtlebot3_ws/install/setup.bash; ros2 launch turtlebot3_bringup rviz2.launch.py`

launch the global localization node(make sure you are in the rover\_ws directory): `source install/setup.bash;ros2 launch localization global_launch.py;`

launch fake encoder node: `source install/setup.bash; ros2 run simulation_localization encoder_sim_node`

#How to run the nodes with no simulation:

you only need to run this: `source install/setup.bash;ros2 launch localization global_launch.py;`

#TODO: 

add noise to sensors and test how the ekf nodes handle them.
