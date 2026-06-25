from launch import LaunchDescription
from launch_ros.actions import Node
import os
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='localization',
            executable='odom_node',
            name='odom_node',
            parameters=[{
                'wheel_radius' : 0.033,
                'wheel_base' : 0.16
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