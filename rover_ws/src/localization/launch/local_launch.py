from launch import LaunchDescription
from launch_ros.actions import Node
from launch.substitutions import LaunchConfiguration
from launch.actions import DeclareLaunchArgument
import os
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    # 1. Declare the use_sim_time argument so it can accept values from the main launch file
    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time',
        default_value='false',
        description='Use simulation clock if true'
    )
    
    use_sim_time = LaunchConfiguration('use_sim_time')

    return LaunchDescription([
        use_sim_time_arg,
        
        # Odometer Node
        Node(
            package='localization',
            executable='odom_node',
            name='odom_node',
            parameters=[{
                'wheel_radius' : 0.033,
                'wheel_base' : 0.16,
                'use_sim_time': use_sim_time # <-- Injected dynamic parameter
            }]
        ),
        
        # Robot Localization EKF Node
        Node(
            package='robot_localization',
            executable='ekf_node',
            name='ekf_local_node',
            # We combine your custom YAML file parameters AND the dynamic use_sim_time parameter
            parameters=[
                os.path.join(get_package_share_directory("localization"), 'params', 'ekf_local_config.yaml'),
                {'use_sim_time': use_sim_time} # <-- Injected dynamic parameter
            ],
            remappings=[
                ('odometry/filtered', '/odom/local')
            ]
        ),
    ])