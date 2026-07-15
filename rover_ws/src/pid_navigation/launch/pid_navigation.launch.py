from launch import LaunchDescription
from launch_ros.actions import Node
import os
from ament_index_python.packages import get_package_share_directory
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource

def generate_launch_description():

    return LaunchDescription([
        Node(
            package='pid_navigation',
            executable='lane_pid_node',
            name='lane_pid_node',
            parameters=[{
                'kp' : 3.0,
                'ki' : 0.0,
                'kd':  5.0,
                'base_linear_vel': 1.38,
                'max_angular_vel': 1.5,
                'max_integral': 1.0
            }]
        ),
        Node(
            package='pid_navigation',
            executable='pothole_pid_node',
            name='pothole_pid_node',
            parameters=[{
                'kp' : 3.0,
                'ki' : 0.0,
                'kd':  1.0,
                'safe_distance': 1.0,
                'max_integral': 1.0
            }]
        )
    ])