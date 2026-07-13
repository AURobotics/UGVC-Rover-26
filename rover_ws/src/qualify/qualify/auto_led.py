import rclpy
from rclpy.node import Node
from std_srvs.srv import SetBool

MANUAL_TOGGLE_TOPIC = '/manual_toggle'


class AutoLed(Node):
    def __init__(self):
        super().__init__("auto_led")
        self.manual_toggle_server = self.create_service(
                        SetBool,
                        MANUAL_TOGGLE_TOPIC,
                        self.manual_toggle_callback
                    )        
        self.auto_led_state = False

    def manual_toggle_callback(self, request, response):
        self.set_led(request.data)
        response.success = True
        return response

    def set_led(self, turn_off):
        if turn_off:
            self.get_logger().info("Turning off auto LED")
            self.auto_led_state = False
        else:
            self.get_logger().info("Turning on auto LED")
            self.auto_led_state = True


def main(args=None):
    rclpy.init(args=args)
    node = AutoLed()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()