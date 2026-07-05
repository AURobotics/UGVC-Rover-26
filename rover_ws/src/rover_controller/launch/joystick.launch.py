
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.substitutions import LaunchConfiguration
from launch.actions import DeclareLaunchArgument

def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time')

    teleop_keyboard_node = Node(
        package='teleop_twist_keyboard',
        executable='teleop_twist_keyboard',
        name='teleop_twist_keyboard_node',
        output='screen',
        prefix='gnome-terminal --',
        parameters=[{'use_sim_time': use_sim_time}],
        remappings=[('/cmd_vel', '/cmd_vel')],  # explicit, no change needed
    )
    twist_stamper = Node(
    package='rover_controller',
    executable='twist_stamper',
    name='twist_stamper',
    parameters=[{'use_sim_time': use_sim_time}],
)


    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Use sim time if true'),
        teleop_keyboard_node,
        # twist_stamper,
    ])