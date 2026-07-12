from launch import LaunchDescription
from launch_ros.actions import Node
import os
from ament_index_python.packages import get_package_share_directory
from launch.actions import IncludeLaunchDescription

from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():
    madgwick_launch = os.path.join(get_package_share_directory('imu_filter_madgwick'), 'launch', 'imu_filter.launch.py')

    return LaunchDescription([
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(madgwick_launch)),
        Node(
            package='localization',
            executable='odom_node',
            name='odom_node',
            parameters=[{ #wheelbase and wheel radias are set to 1 by default, which means that converting rad/s to m/s is skipped
                'hard_iron' : [ 9.57074267, 0.5361896, -5.28439552],
                'soft_iron' : [1.19548172,0.03502767, 0.02766672,
                               0.03502767, 1.14443211, 0.0648242,
                               0.02766672, 0.0648242,  1.62894913],
                'linear_scale_factor': 1.0,
                'angular_scale_factor': 1.0
            }]
        ),
        Node(
            package='robot_localization',
            executable='ekf_node',
            name='ekf_local_node',
            parameters=[os.path.join(get_package_share_directory("localization"), 'params', 'ekf_local_config.yaml')],
            remappings=[
                ('odometry/filtered', '/odom/local')
            ]
        ),
    ])