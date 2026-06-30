from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    declare_params_file = DeclareLaunchArgument(
        'params_file',
        default_value=PathJoinSubstitution([
            FindPackageShare('mission'),
            'config',
            'params.yaml'
        ]),
        description='Path to YAML parameter file'
    )

    mission_node = Node(
        package='mission',
        executable='mission_node',
        name='mission_node',
        output='screen',
        parameters=[
            LaunchConfiguration('params_file'),
        ],
    )

    return LaunchDescription([
        declare_params_file,
        mission_node
    ])