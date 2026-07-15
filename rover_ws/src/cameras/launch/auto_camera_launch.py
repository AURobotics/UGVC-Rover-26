# road_detector_launch.py
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='cameras',
            executable='internal_camera_node',
            name='camera',
            parameters=[{
                'device_index': 4,
                'publish_rate': 15.0,
                'topic': '/camera/image_raw',
                'frame_id': 'camera',
            }],
            output='screen'
        ),
    ])