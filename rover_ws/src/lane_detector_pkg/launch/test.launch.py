from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([

        Node(
            package='lane_detector_pkg',
            executable='vedioPublisher',
            output='screen'
        ),


        Node(
            package='lane_detector_pkg',
            executable='lanes_obstacles_error',
            output='screen'
        ),

       # Node(
       #     package='lane_detector_pkg',
       #     executable='errors_percentage',
       #     output='screen'
       # ),
    ])