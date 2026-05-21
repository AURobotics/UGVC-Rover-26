from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare
from launch_ros.actions import Node

def generate_launch_description():
    # =============================================================
    # DECLARE LAUNCH ARGUMENTS
    # =============================================================
    
    declare_params_file = DeclareLaunchArgument(
        'params_file',
        default_value=PathJoinSubstitution([
            FindPackageShare('road_detector'),
            'config',
            'params.yaml'
        ]),
        description='Path to YAML parameter file'
    )
    
    # Core parameters
    declare_camera_topic = DeclareLaunchArgument(
        'camera_topic',
        default_value='',
        description='Override camera topic'
    )
    
    declare_camera_height = DeclareLaunchArgument(
        'camera_height',
        default_value='',
        description='Override camera height'
    )

    declare_pitch_deg = DeclareLaunchArgument(
        'pitch_deg',
        default_value='-50.0',
        description='Camera pitch angle (degrees, negative = downward)'
    )
    
    # Camera intrinsics
    declare_fx = DeclareLaunchArgument('fx', default_value='1000.0')
    declare_fy = DeclareLaunchArgument('fy', default_value='1000.0')
    declare_cx = DeclareLaunchArgument('cx', default_value='960.0')
    declare_cy = DeclareLaunchArgument('cy', default_value='540.0')
    
    # Detection parameters
    declare_min_radius = DeclareLaunchArgument('min_radius', default_value='10')
    declare_max_radius = DeclareLaunchArgument('max_radius', default_value='200')
    
    declare_publish_debug_images = DeclareLaunchArgument('publish_debug_images', default_value='false')
    declare_publish_performance_stats = DeclareLaunchArgument('publish_performance_stats', default_value='false')

    # =============================================================
    # CONFIGURE NODE
    # =============================================================
    
    road_detector_node = Node(
        package='road_detector',
        executable='road_detector_node',
        name='road_detector',
        output='screen',
        emulate_tty=True,  # Better logging for debugging
        parameters=[
            LaunchConfiguration('params_file'),
            {
                'camera_topic': LaunchConfiguration('camera_topic'),
                'camera_height': LaunchConfiguration('camera_height'),
                'pitch_deg': LaunchConfiguration('pitch_deg'),
                'fx': LaunchConfiguration('fx'),
                'fy': LaunchConfiguration('fy'),
                'cx': LaunchConfiguration('cx'),
                'cy': LaunchConfiguration('cy'),
                'min_radius': LaunchConfiguration('min_radius'),
                'max_radius': LaunchConfiguration('max_radius'),
                'publish_debug_images': LaunchConfiguration('publish_debug_images'),
                'publish_performance_stats': LaunchConfiguration('publish_performance_stats'),
            }
        ],
        remappings=[
            ('/road_detector/pointcloud', '/local_costmap/obstacle_points'),
        ],
    )

    return LaunchDescription([
        declare_params_file,
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
        road_detector_node,
    ])