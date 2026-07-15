import os
from ament_index_python import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node

def generate_launch_description():
    rover_embedded_dir = get_package_share_directory('rover_embedded')
    motion_dir = get_package_share_directory('motion')
    camera_dir = get_package_share_directory('cameras')

    # Renamed to avoid argument namespace conflicts
    declare_lane_params_file = DeclareLaunchArgument(
        'lane_params_file',
        default_value=PathJoinSubstitution([
            FindPackageShare('road_detector'),
            'config',
            'lane_follower_params.yaml'
        ]),
        description='Path to YAML parameter file for lane follower'
    )
    
    declare_road_params_file = DeclareLaunchArgument(
        'road_params_file',
        default_value=PathJoinSubstitution([
            FindPackageShare('road_detector'),
            'config',
            'params.yaml'
        ]),
        description='Path to YAML parameter file for road detector'
    )

    lane_follower_node = Node(
        package='road_detector',
        executable='lane_follower_node',
        name='lane_follower',
        output='screen',
        emulate_tty=True,
        parameters=[
            LaunchConfiguration('lane_params_file'),
        ],
    )

    road = Node(
        package='road_detector',
        executable='road_detector_node',
        name='road_detector',
        output='screen',
        emulate_tty=True,
        parameters=[
            LaunchConfiguration('road_params_file'),
        ],
    )

    # FIXED: Wrapped in IncludeLaunchDescription
    camera = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(camera_dir, 'launch', 'camera_launch.py')
        )
    )

    stm_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(rover_embedded_dir, 'launch', 'stm_launch.py')
        )
    )

    cmd_mux_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(motion_dir, 'launch', 'cmd_mux.launch.py')
        )
    )

    return LaunchDescription([
        declare_road_params_file,
        road,
        declare_lane_params_file,
        lane_follower_node,
        camera,
        stm_launch,
        cmd_mux_launch,
    ])