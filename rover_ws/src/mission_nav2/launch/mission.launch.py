"""
mission_launch.py
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
from launch.conditions import IfCondition


def generate_launch_description():
    nav2_bringup_dir = get_package_share_directory("nav2_bringup")

    params_file_arg = DeclareLaunchArgument(
        "params_file",
        default_value=os.path.join(
            get_package_share_directory("mission_nav2"),
            "config", "nav2_params2.yaml"),
        description="Full path to the Nav2 params file to use",
    )
    
    # Keep the default as false so it defaults to real hardware, 
    # but we can easily toggle it from the CLI for simulation.
    use_sim_time_arg = DeclareLaunchArgument(
        "use_sim_time", default_value="false",
        description="Use simulation clock if true",
    )

    params_file = LaunchConfiguration("params_file")
    use_sim_time = LaunchConfiguration("use_sim_time")

    declare_use_rviz = DeclareLaunchArgument(
        'use_rviz', default_value='true',
        description='Launch RViz2')
    use_rviz     = LaunchConfiguration('use_rviz')

    # ------------------------------------------------------------------ #
    #  RViz                                                              #
    # ------------------------------------------------------------------ #
    rover_nav_dir = get_package_share_directory('rover_navigation')
    rviz = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(rover_nav_dir, 'launch', 'rvizz.launch.py')
        ),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'rviz_config':  os.path.join(rover_nav_dir, 'rviz', 'rover_teleop.rviz'),
        }.items(),
        condition=IfCondition(use_rviz),
    )

    # ---- 1. Sensors / Localization -----------------------------------
    localization_node = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory("localization"), "launch", "local_launch.py")
        ),
        launch_arguments={"use_sim_time": use_sim_time}.items(),
    )

    # ---- 2. Nav2 Navigation Stack -------------------------------------------
    navigation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_bringup_dir, "launch", "navigation_launch.py")
        ),
        launch_arguments={
            "params_file": params_file,
            "use_sim_time": use_sim_time,
            "autostart": "true",
        }.items(),
    )

    # ---- 3. Mission Manager -------------------------------------------------
    mission_manager = Node(
        package="mission_nav2",
        executable="waypoint_navigation",
        name="mission_manager",
        output="screen",
        parameters=[{"use_sim_time": use_sim_time}],
    )
    delayed_mission_manager = TimerAction(period=10.0, actions=[mission_manager])

    # ---- 4. Road Detector Node ----------------------------------------------
    road_detector_node = Node(
        package='road_detector',
        executable='road_detector_node',
        name='road_detector',
        # FIXED: Changed from hardcoded {'use_sim_time': True} to use the variable tracking use_sim_time
        parameters=[
            os.path.join(get_package_share_directory('road_detector'), 'config', 'params_sim.yaml'),
            {'use_sim_time': use_sim_time} 
        ],
        additional_env={'PYTHONUNBUFFERED': '1'},
        output='screen'
    )

    return LaunchDescription([
        params_file_arg,
        use_sim_time_arg,
        declare_use_rviz,
        rviz,
        road_detector_node,
        localization_node,
        navigation,
        delayed_mission_manager,
    ])

    # for sim time:
    # ros2 launch mission_nav2 mission.launch.py use_sim_time:=true