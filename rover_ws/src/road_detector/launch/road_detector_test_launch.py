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

    declare_camera_topic = DeclareLaunchArgument(
        'camera_topic',
        default_value='',
        description='Override camera topic for road_detector',
    )
    declare_camera_height = DeclareLaunchArgument(
        'camera_height',
        default_value='',
        description='Override camera height (m)',
    )
    declare_pitch_deg = DeclareLaunchArgument(
        'pitch_deg',
        default_value='-50.0',
        description='Camera pitch angle (degrees, negative = downward)',
    )
    declare_fx = DeclareLaunchArgument('fx', default_value='1000.0')
    declare_fy = DeclareLaunchArgument('fy', default_value='1000.0')
    declare_cx = DeclareLaunchArgument('cx', default_value='960.0')
    declare_cy = DeclareLaunchArgument('cy', default_value='540.0')
    declare_min_radius = DeclareLaunchArgument('min_radius', default_value='10')
    declare_max_radius = DeclareLaunchArgument('max_radius', default_value='200')
    declare_publish_debug_images = DeclareLaunchArgument(
        'publish_debug_images', default_value='true'
    )
    declare_publish_performance_stats = DeclareLaunchArgument(
        'publish_performance_stats', default_value='false'
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

    declare_video_path = DeclareLaunchArgument(
        'video_path',
        default_value='',
        description='Override path to the video file',
    )
    declare_publish_rate = DeclareLaunchArgument(
        'publish_rate',
        default_value='30.0',
        description='Video publish rate in Hz',
    )
    declare_loop = DeclareLaunchArgument(
        'loop',
        default_value='true',
        description='Loop the video when it ends',
    )
    declare_frame_id = DeclareLaunchArgument(
        'frame_id',
        default_value='camera',
        description='frame_id written into every published Image header',
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

    declare_output_file = DeclareLaunchArgument(
        'output_file',
        default_value='/tmp/pointcloud_log.txt',
        description='Path of the output log file written by pointcloud_logger',
    )
    declare_pointcloud_topic = DeclareLaunchArgument(
        'pointcloud_topic',
        default_value='/road_detector/pointcloud',
        description='PointCloud2 topic for the logger to subscribe to',
    )
    declare_max_points_to_log = DeclareLaunchArgument(
        'max_points_to_log',
        default_value='50',
        description='Max points written per cloud (0 = all)',
    )
    declare_log_every_n = DeclareLaunchArgument(
        'log_every_n',
        default_value='1',
        description='Log every Nth received message',
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
            {
                'camera_topic':              LaunchConfiguration('camera_topic'),
                'camera_height':             LaunchConfiguration('camera_height'),
                'pitch_deg':                 LaunchConfiguration('pitch_deg'),
                'fx':                        LaunchConfiguration('fx'),
                'fy':                        LaunchConfiguration('fy'),
                'cx':                        LaunchConfiguration('cx'),
                'cy':                        LaunchConfiguration('cy'),
                'min_radius':                LaunchConfiguration('min_radius'),
                'max_radius':                LaunchConfiguration('max_radius'),
                'publish_debug_images':      LaunchConfiguration('publish_debug_images'),
                'publish_performance_stats': LaunchConfiguration('publish_performance_stats'),
            },
        ],
        remappings=[
            # Keep the same remapping as the original launch file so the
            # pointcloud_logger's topic argument can be updated to match.
            ('/road_detector/pointcloud', '/local_costmap/obstacle_points'),
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
            {
                # Only override when the launch argument was explicitly set
                'video_path':    LaunchConfiguration('video_path'),
                'publish_rate':  LaunchConfiguration('publish_rate'),
                'loop':          LaunchConfiguration('loop'),
                'frame_id':      LaunchConfiguration('frame_id'),
                # image_topic is driven by the params file; road_detector's
                # camera_topic launch arg acts as the single source of truth
                # — keep them in sync via the params files.
            },
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
            {
                # road_detector remaps its output to /local_costmap/obstacle_points,
                # so the logger must subscribe to the remapped topic.
                'pointcloud_topic':   LaunchConfiguration('pointcloud_topic'),
                'output_file':        LaunchConfiguration('output_file'),
                'max_points_to_log':  LaunchConfiguration('max_points_to_log'),
                'log_every_n':        LaunchConfiguration('log_every_n'),
            },
        ],
        # Mirror the same remapping so the logger always follows wherever
        # road_detector publishes its point cloud.
        remappings=[
            ('/road_detector/pointcloud', '/local_costmap/obstacle_points'),
        ],
    )

    # =========================================================================
    # LAUNCH DESCRIPTION
    # =========================================================================

    return LaunchDescription([
        # road_detector args
        declare_rd_params_file,
        declare_camera_topic,
        declare_camera_height,
        declare_pitch_deg,
        declare_fx,
        declare_fy,
        declare_cx,
        declare_cy,
        declare_min_radius,
        declare_max_radius,
        declare_publish_debug_images,
        declare_publish_performance_stats,

        # video_publisher args
        declare_vp_params_file,
        declare_video_path,
        declare_publish_rate,
        declare_loop,
        declare_frame_id,

        # pointcloud_logger args
        declare_pcl_params_file,
        declare_output_file,
        declare_pointcloud_topic,
        declare_max_points_to_log,
        declare_log_every_n,

        # Nodes
        video_publisher_node,
        road_detector_node,
        pointcloud_logger_node,
    ])
