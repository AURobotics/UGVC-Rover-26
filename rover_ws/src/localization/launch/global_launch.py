import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import AppendEnvironmentVariable
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    local_launch = os.path.join(get_package_share_directory('localization'), 'launch', 'local_launch.py')

    return LaunchDescription([
        IncludeLaunchDescription(
        PythonLaunchDescriptionSource(local_launch)),
        # Node(
        #     package='robot_localization',
        #     executable='ekf_node',
        #     name='ekf_local_node',
        #     parameters=[os.path.join(get_package_share_directory("localization"), 'params', 'ekf_local_config.yaml')],
        #     remappings=[
        #         ('odometry/filtered', '/odom/local')
        #     ]
        # ),
        Node(
            package='robot_localization',
            executable='navsat_transform_node',
            name='navsat_transform_node',
            parameters=[os.path.join(get_package_share_directory("localization"), 'params', 'navsat_config.yaml')],
            remappings=[
                ('odometry/filtered', '/odom/local'),
                ('gps/fix', '/phyphox/gps')
            ]
        ),
        Node(
            package='robot_localization',
            executable='ekf_node',
            name='ekf_global_node',
            parameters=[os.path.join(get_package_share_directory("localization"), 'params', 'ekf_global_config.yaml')],
            remappings=[
                ('odometry/filtered', '/odom/global')
            ]
        ),
    ])
