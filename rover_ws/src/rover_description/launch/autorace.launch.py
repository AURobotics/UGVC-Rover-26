import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (IncludeLaunchDescription, SetEnvironmentVariable,
                             DeclareLaunchArgument,TimerAction, RegisterEventHandler)
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
import xacro

def generate_launch_description():

    package_name = 'rover_description'
    rover_desc = get_package_share_directory('rover_description')
    gz_model_path = os.path.join(rover_desc, 'gz_model')
    tb3_desc    = get_package_share_directory('turtlebot3_description')
    tb3_gz      = get_package_share_directory('turtlebot3_gazebo')
    set_gz_path = SetEnvironmentVariable(
        'GZ_SIM_RESOURCE_PATH',
        os.path.join(rover_desc, 'gz_model') +
        ':' +
        os.path.dirname(tb3_desc)  # lets Gazebo find TB3 meshes
    )
    
    pkg_share = get_package_share_directory(package_name)
    world_file = os.path.join(pkg_share, 'worlds', 'autorace.world')
    # ── TurtleBot3 model must be set ───────────────────────────────────
    set_tb3_model = SetEnvironmentVariable('TURTLEBOT3_MODEL', 'waffle')
    tb3_model_path = os.path.join(
    tb3_gz,
    'models', 'turtlebot3_waffle', 'model.sdf'
    )
    
    rsp = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([os.path.join(pkg_share, 'launch', 'rsp.launch.py')]),
        launch_arguments={'use_sim_time': 'true'}.items()
    )

    # ✅ Use 'gz_args' not 'world', and pass -r to auto-run simulation
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([os.path.join(
            get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py')]),
        launch_arguments={
            'gz_args': '-r ' + world_file,
            'on_exit_shutdown': 'true'
        }.items()
    )
    clock_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='clock_bridge',
        arguments=['/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock'],
        parameters=[{'use_sim_time': False}],  # ← False here, it IS the clock source
        output='screen'
    )

    ros_gz_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='sensor_bridge',
            arguments=[
        '/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan',
        '/imu@sensor_msgs/msg/Imu[gz.msgs.IMU',
        '/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist',
        '/tf@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V',
        '/tf_static@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V',
        '/scan/points@sensor_msgs/msg/PointCloud2[gz.msgs.PointCloudPacked',
        '/camera/image_raw@sensor_msgs/msg/Image[gz.msgs.Image',
        '/camera/depth_image@sensor_msgs/msg/Image[gz.msgs.Image',
        '/camera/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo',
        '/camera/points@sensor_msgs/msg/PointCloud2[gz.msgs.PointCloudPacked',
        
    ],
        remappings=[
            ('/camera/depth_image', '/camera/depth/image_raw'),
            ('/camera/camera_info', '/camera/camera_info'),
        ],
            parameters=[{
            'use_sim_time': True,
            'qos_overrides./tf_static.publisher.durability': 'transient_local',
        }],
        output='screen'
    )

    spawn_entity = Node(
    package='ros_gz_sim',
    executable='create',
    arguments=[
        '-file', tb3_model_path,   # ← use -file instead of -topic
        '-name', 'turtlebot3_waffle',
        '-x', '0.4',
        '-y', '-1.75',
        '-z', '0.05',
        '-Y', '1.5707'
    ]
)

    delayed_spawn = TimerAction(period=8.0, actions=[spawn_entity])
    delayed_rsp = TimerAction(period=2.0, actions=[rsp])

    joint_state_publisher = TimerAction(
    period=6.0,  # wait 2 seconds after RSP starts
    actions=[
        Node(
            package='joint_state_publisher',
            executable='joint_state_publisher',
            name='joint_state_publisher',
            parameters=[{'use_sim_time': True}],
            output='screen',
        )
    ]
)
    return LaunchDescription([
        set_gz_path,
        set_tb3_model,
        clock_bridge,
        gazebo,
        ros_gz_bridge,   # bridge must be running before spawn
        delayed_rsp,
        delayed_spawn,
        joint_state_publisher,
    ])