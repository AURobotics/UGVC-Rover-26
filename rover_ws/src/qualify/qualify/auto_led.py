import rclpy
from rclpy.node import Node
from std_srvs.srv import SetBool
from std_msgs.msg import Bool

MANUAL_TOGGLE_TOPIC = '/manual_toggle'
STM_LED_TOPIC = '/rover/mode'


class AutoLed(Node):
    def __init__(self):
        super().__init__("auto_led")
        self.manual_toggle_server = self.create_service(
                        SetBool,
                        MANUAL_TOGGLE_TOPIC,
                        self.manual_toggle_callback
                    )     
        self.stm_led_publisher = self.create_publisher(
            Bool,
            STM_LED_TOPIC,
            10
        ) 
        self.auto_led_state = False
        self.create_timer(0.1, self.publish_led_state)  

        # self.test_subscriber()

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

    def publish_led_state(self):
        msg = Bool()
        msg.data = self.auto_led_state
        self.stm_led_publisher.publish(msg)

    # def test_subscriber(self):
    #     self.create_subscription(
    #         Bool,
    #         STM_LED_TOPIC,
    #         self.led_callback,
    #         10
    #     )
    # def led_callback(self, msg):
    #     self.get_logger().info(f"led is: {msg.data}")


def main(args=None):
    rclpy.init(args=args)
    node = AutoLed()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()