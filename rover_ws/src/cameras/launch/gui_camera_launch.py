# road_detector_launch.py
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='cameras',
            executable='external_camera_node',
            name='camera1',
            parameters=[{
                'device_index': 4,
                'publish_rate': 15.0,
                'topic': '/camera1/image_raw',
                'frame_id': 'camera1',
            }],
            output='screen'
        ),
    ])