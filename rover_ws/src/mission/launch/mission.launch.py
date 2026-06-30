from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    mission_node = Node(
        package='mission',
        executable='mission_node',
        name='mission_node',
        output='screen',
        parameters=[{
        }]
    )

    return LaunchDescription([
        mission_node
    ])