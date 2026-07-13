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
            parameters=[{ #turtlebot3 parameters
                'wheel_radius' : 0.033,
                'wheel_base' : 0.16,
                'linear_scale_factor': 0.82,
                'angular_scale_factor': 0.7272
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
        Node(
            package='localization',
            executable='encoder_sim_node',
            name='encoder_sim_node',
        ),
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            arguments=['0.0', '0.0', '0.0', '0.0', '0.0', '0.0', 'base_link', 'burger/imu_link/tb3_imu']
        )
    ])