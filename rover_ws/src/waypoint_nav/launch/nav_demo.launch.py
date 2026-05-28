import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
  
    pkg_dir = get_package_share_directory('waypoint_nav')
    waypoints_file_path = os.path.join(pkg_dir, 'config', 'waypoints.yaml')
    rviz_config_path = os.path.join(pkg_dir, 'rviz', 'nav_config.rviz')

    
    sim_time_arg = {'use_sim_time': True}

    trajectory_node = Node(
        package='waypoint_nav',
        executable='trajectory',
        name='trajectory_node',
        parameters=[{
            'waypoints_file': waypoints_file_path,
            'control_scale': 0.3,
            'min_control_dist': 0.2,
            'points_per_meter': 15,
            'republish_rate_sec': 2.0,
            'use_sim_time': True  
        }],
        output='screen'
    )

    controller_node = Node(
        package='waypoint_nav',
        executable='controller',
        name='controller_node',
        parameters=[{
            'lookahead_distance': 1.5,
            'desired_velocity': 0.2,
            'goal_threshold': 0.15,
            'use_sim_time': True 
        }],
        output='screen'
    )

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config_path],
        parameters=[{'use_sim_time': True}],  
        output='screen'
    )

    return LaunchDescription([
        trajectory_node,
        controller_node,  
        rviz_node
    ])