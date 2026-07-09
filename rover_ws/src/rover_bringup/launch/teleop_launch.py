#!/usr/bin/env python3
import os
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, ExecuteProcess, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    rover_embedded_dir = get_package_share_directory('rover_embedded')
    motion_dir = get_package_share_directory('motion')

    teleop_params = os.path.join(motion_dir, 'config', 'teleop_params.yaml')

    stm_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(rover_embedded_dir, 'launch', 'stm_launch.py')
        )
    )

    convertor_node= Node(
        package='motion',
        executable='twist_node',
        name='twist_node',
        output='screen',
        parameters=[{
            'wheel_base': 0.30,
        }],
    )

    teleop_node = Node(
        package='teleop_twist_keyboard',
        executable='teleop_twist_keyboard',
        name='teleop_twist_keyboard',
        output='screen',
        prefix='gnome-terminal --',
        parameters=[teleop_params],
    )


    return LaunchDescription([
        stm_launch,
        convertor_node,
        teleop_node,
    ])