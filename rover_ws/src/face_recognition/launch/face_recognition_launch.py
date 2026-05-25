from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([

        Node(
            package='face_recognition',
            executable='camera_publisher_node',
            name='camera_publisher_node',
            output='screen'
        ),

        Node(
            package='face_recognition',
            executable='face_recognition_node',
            name='face_recognition_node',
            output='screen'
        ),

    ])