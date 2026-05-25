# road_detector_launch.py
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='cameras',
            executable='camera_node',
            name='camera1',
            parameters=[{
                'device_index': 0,
                'publish_rate': 30.0,
                'topic': '/camera1/image_raw',
                'frame_id': 'camera1',
            }],
            output='screen'
        ),
        Node(
            package='cameras',
            executable='camera_node',
            name='camera2',
            parameters=[{
                'device_index': 2,
                'publish_rate': 30.0,
                'topic': '/camera2/image_raw',
                'frame_id': 'camera2',
            }],
            output='screen'
        ),
    ])