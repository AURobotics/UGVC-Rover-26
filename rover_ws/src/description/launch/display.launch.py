import os
from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    
    # Get the package directory
    pkg_dir = get_package_share_directory('rover_description')
    
    # Path to URDF
    urdf_file = os.path.join(pkg_dir, 'urdf', 'rover.urdf')
    
    # Read the URDF file
    with open(urdf_file, 'r') as file:
        robot_description = file.read()
    
    return LaunchDescription([
        
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            output='screen',
            parameters=[{'robot_description': robot_description}]
        ),
        
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='world_to_base',
            arguments=['--x', '0', '--y', '0', '--z', '0',
                        '--roll', '0', '--pitch', '0', '--yaw', 
                        '0', '--frame-id', 'world', '--child-frame-id', 'base_link']
            ),
        
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2'
        )
    ])