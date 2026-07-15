#!/usr/bin/env python3

import os
from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    pkg_dir = get_package_share_directory('motion')
    params = os.path.join(pkg_dir, 'config', 'cmd_mux_params.yaml')

    return LaunchDescription([
        Node(
            package='motion',
            executable='twist_node',
            name='twist_node',
            output='screen',
            emulate_tty=True,
            parameters=[params],
        ),
    ])