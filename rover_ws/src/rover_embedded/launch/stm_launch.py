from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():

    port_arg = DeclareLaunchArgument(
        'port',
        default_value='/dev/ttyACM0',
        description='Serial port for the STM32 (e.g. /dev/ttyACM0)',
    )
    linear_speed_arg = DeclareLaunchArgument(
        'linear_speed',
        default_value='0.5',
        description='Max linear speed sent by the teleop node (m/s)',
    )
    angular_speed_arg = DeclareLaunchArgument(
        'angular_speed',
        default_value='1.0',
        description='Max angular speed sent by the teleop node (rad/s)',
    )
    wheel_base_arg = DeclareLaunchArgument(
        'wheel_base',
        default_value='0.30',
        description='Distance between left and right wheels (m)',
    )

   
    stm32_node = Node(
        package='rover_embedded',       
        executable='stm_node',
        name='stm_node',
        output='screen',
        emulate_tty=True,
        parameters=[
            {'port': LaunchConfiguration('port')},
        ],
    )
    converter_node = Node(
        package='rover_embedded',          
        executable='twist_node',
        name='twist_node',
        output='screen',
        parameters=[{
            'wheel_base': LaunchConfiguration('wheel_base'),
        }],
    )


    teleop_node = Node(
        package='teleop_twist_keyboard',
        executable='teleop_twist_keyboard',
        name='teleop_twist_keyboard',
        output='screen',
        emulate_tty=True,         
        prefix='terminator -x',         
        parameters=[{
            'speed':       LaunchConfiguration('linear_speed'),
            'turn':        LaunchConfiguration('angular_speed'),
            'repeat_rate': 10.0,    
            'key_timeout':  0.6,    
        }],
    )

    return LaunchDescription([
        port_arg,
        linear_speed_arg,
        angular_speed_arg,
        wheel_base_arg,
        stm32_node,
        converter_node,
        teleop_node,
    ])