#!/usr/bin/env python3
import os
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    rover_embedded_dir = get_package_share_directory('rover_embedded')
    motion_dir = get_package_share_directory('motion')
    mission_dir = get_package_share_directory('mission')

    stm_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(rover_embedded_dir, 'launch', 'stm_launch.py')
        )
    )

    cmd_mux_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(motion_dir, 'launch', 'cmd_mux.launch.py')
        )
    )

    servo_cam_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(motion_dir, 'launch', 'servo_cam.launch.py')
        )
    )

    mission_launch=IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(mission_dir, 'launch', 'mission_manual.launch.py')
        )
    )

    return LaunchDescription([
        stm_launch,
        cmd_mux_launch,
        servo_cam_launch,
        mission_launch,
    ])