import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    # 1. Locate paths
    rover_nav_dir = get_package_share_directory('rover_nav')
    nav2_bringup_dir = get_package_share_directory('nav2_bringup')
    
    # 2. Declare configurations
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    params_file = LaunchConfiguration('params_file', default=os.path.join(rover_nav_dir, 'config', 'nav2_params.yaml'))

    # 3. Include official Nav2 Bringup launch
    # This automatically runs the controller server, planner server, recovery server, and lifecycle manager
    nav2_bringup_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(nav2_bringup_dir, 'launch', 'navigation_launch.py')),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'params_file': params_file
        }.items()
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true', description='Use simulation clock'),
        DeclareLaunchArgument('params_file', default_value=os.path.join(rover_nav_dir, 'config', 'nav2_params.yaml')),
        
        nav2_bringup_launch
    ])