from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare
from launch_ros.actions import Node


def generate_launch_description():
    # =========================================================================
    # DECLARE LAUNCH ARGUMENTS — road_detector
    # =========================================================================

    declare_rd_params_file = DeclareLaunchArgument(
        'rd_params_file',
        default_value=PathJoinSubstitution([
            FindPackageShare('road_detector'),
            'config',
            'params.yaml',
        ]),
        description='Path to road_detector YAML parameter file',
    )

    # =========================================================================
    # DECLARE LAUNCH ARGUMENTS — video_publisher
    # =========================================================================

    declare_vp_params_file = DeclareLaunchArgument(
        'vp_params_file',
        default_value=PathJoinSubstitution([
            FindPackageShare('road_detector'),
            'config',
            'video_publisher_params.yaml',
        ]),
        description='Path to video_publisher YAML parameter file',
    )

    # =========================================================================
    # DECLARE LAUNCH ARGUMENTS — pointcloud_logger
    # =========================================================================

    declare_pcl_params_file = DeclareLaunchArgument(
        'pcl_params_file',
        default_value=PathJoinSubstitution([
            FindPackageShare('road_detector'),
            'config',
            'pointcloud_logger_params.yaml',
        ]),
        description='Path to pointcloud_logger YAML parameter file',
    )

    # =========================================================================
    # NODE — road_detector  (unchanged from original launch file)
    # =========================================================================

    road_detector_node = Node(
        package='road_detector',
        executable='road_detector_node',
        name='road_detector',
        output='screen',
        emulate_tty=True,
        parameters=[
            LaunchConfiguration('rd_params_file'),
        ],
    )

    # =========================================================================
    # NODE — video_publisher
    # =========================================================================

    video_publisher_node = Node(
        package='road_detector',
        executable='video_publisher_node',
        name='video_publisher',
        output='screen',
        emulate_tty=True,
        parameters=[
            LaunchConfiguration('vp_params_file'),
        ],
    )

    # =========================================================================
    # NODE — pointcloud_logger
    # =========================================================================

    pointcloud_logger_node = Node(
        package='road_detector',
        executable='pointcloud_logger_node',
        name='pointcloud_logger',
        output='screen',
        emulate_tty=True,
        parameters=[
            LaunchConfiguration('pcl_params_file'),
        ],
    )

    # =========================================================================
    # LAUNCH DESCRIPTION
    # =========================================================================

    return LaunchDescription([
        # road_detector args
        declare_rd_params_file,
        # video_publisher args
        declare_vp_params_file,
        # pointcloud_logger args
        declare_pcl_params_file,

        # Nodes
        video_publisher_node,
        road_detector_node,
        pointcloud_logger_node,
    ])
