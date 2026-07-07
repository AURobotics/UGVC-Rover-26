import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    pkg_dir = get_package_share_directory('waypoint_nav')
    waypoints_file_path = os.path.join(pkg_dir, 'config', 'waypoints.yaml')
    rviz_config_path = os.path.join(pkg_dir, 'rviz', 'nav_config.rviz')

    bezier_server_node = Node(
        package='waypoint_nav',
        executable='trajectory',
        name='bezier_path_server',
        parameters=[{
            'control_scale': 0.3,
            'min_control_dist': 0.2,
            'points_per_meter': 15,
            'use_sim_time': True
        }],
        output='screen'
    )

    bezier_client_node = Node(
        package='waypoint_nav',
        executable='controller',
        name='bezier_path_client',
        parameters=[{
            'waypoints_file': waypoints_file_path,
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
        bezier_server_node,
        bezier_client_node,
        rviz_node
    ])