from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    cameras_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([FindPackageShare('cameras'), 'launch', 'launch.py'])
        ])
    )
    #IMPORTANT:
    #       I am depending on args in the caneras launch file
    #       should I pass them here? 

    face_recognition_node = Node(
            package='face_recognition',
            executable='face_recognition_node',
            name='face_recognition_node',
    )
    
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
        cameras_launch,
        face_recognition_node,
        declare_params_file,
        mission_node,
    ])