from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare
from launch_ros.actions import Node

def generate_launch_description():
   
    declare_params_file = DeclareLaunchArgument(
        'params_file',
        default_value=PathJoinSubstitution([
            FindPackageShare('road_detector'),
            'config',
            'lane_follower_params.yaml'
        ]),
        description='Path to YAML parameter file'
    )

    lane_follower_node = Node(
        package='road_detector',
        executable='lane_follower_node',
        name='lane_follower',
        output='screen',
        emulate_tty=True,  # Better logging for debugging
        parameters=[
            LaunchConfiguration('params_file'),
        ],
    )

    return LaunchDescription([
        declare_params_file,
        lane_follower_node
    ])