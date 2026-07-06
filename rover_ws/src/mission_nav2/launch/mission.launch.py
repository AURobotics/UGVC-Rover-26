"""
mission_launch.py

Brings up:
  1. Your sensor / localization nodes (placeholders below -- fill in).
  2. Nav2's navigation stack (controller, planner, behavior, bt_navigator,
     waypoint_follower, velocity_smoother, lifecycle_manager) using your
     custom nav2_params.yaml.
  3. lane_mode_manager.py, delayed until Nav2 is actually active so it
     doesn't try to call action/parameter servers that don't exist yet.

Usage:
  ros2 launch <your_package> mission_launch.py \
      params_file:=/path/to/nav2_params.yaml
"""

import os

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    TimerAction,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    nav2_bringup_dir = get_package_share_directory("nav2_bringup")

    params_file_arg = DeclareLaunchArgument(
        "params_file",
        default_value=os.path.join(
            get_package_share_directory("mission_nav2"),
            "config", "nav2_params2.yaml"),
        description="Full path to the Nav2 params file to use",
    )
    use_sim_time_arg = DeclareLaunchArgument(
        "use_sim_time", default_value="false",
        description="Use simulation clock if true",
    )

    params_file = LaunchConfiguration("params_file")
    use_sim_time = LaunchConfiguration("use_sim_time")

    # ---- 1. Your sensors / localization -----------------------------------
    # Replace these with your actual lidar driver, lane/pothole perception
    # nodes, and localization stack (or include their own launch files).
    #
    # lidar_node = Node(
    #     package="your_lidar_driver", executable="lidar_node",
    #     name="lidar", output="screen",
    # )
    localization_node = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory("localization"), "launch", "local_launch.py")
        ),
        launch_arguments={"use_sim_time": use_sim_time}.items(),
    )

    # ---- 2. Nav2 navigation stack -------------------------------------------
    navigation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_bringup_dir, "launch", "navigation_launch.py")
        ),
        launch_arguments={
            "params_file": params_file,
            "use_sim_time": use_sim_time,
            "autostart": "true",   # let the lifecycle_manager auto configure+activate
        }.items(),
    )

    # ---- 3. Mission manager, delayed so Nav2 is active first ---------------
    # A fixed delay is the simplest approach. For a more robust startup,
    # replace this with a check on the lifecycle_manager_navigation's
    # /lifecycle_manager_navigation/is_active service or subscribe to
    # /bond, and only launch the node once that returns true.
    mission_manager = Node(
        package="mission_nav2",
        executable="all_waypoint_navigation.py",
        name="mission_manager",
        output="screen",
        parameters=[{"use_sim_time": use_sim_time}],
    )
    delayed_mission_manager = TimerAction(period=10.0, actions=[mission_manager])

    return LaunchDescription([
        params_file_arg,
        use_sim_time_arg,
        # lidar_node,
        localization_node,
        navigation,
        delayed_mission_manager,
    ])