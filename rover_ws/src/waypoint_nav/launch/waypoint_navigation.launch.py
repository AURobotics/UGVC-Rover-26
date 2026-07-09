import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    pkg_dir = get_package_share_directory('waypoint_nav')

    return LaunchDescription([
        Node(
            package='waypoint_nav',
            executable='trajectory',
            name='bezier_path_server',
            parameters=[{
                'control_scale': 0.3,
                'min_control_dist': 0.2,
                'points_per_meter': 15,
                'use_sim_time': True
            }],
            output='screen',
            remappings=[('/odom', '/odom/global')]
        )
    ])
