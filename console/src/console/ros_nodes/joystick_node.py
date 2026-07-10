import threading
from collections.abc import Callable
import platform
from rclpy.parameter import Parameter
import pyglet
import pyglet.window 
if platform.system() == "Linux":
    pyglet.options.headless = True
from pyglet.input import Controller, ControllerManager
from rclpy.node import Node
from sensor_msgs.msg import Joy

class JoystickNode(Node):
    TICK_INTERVAL_SEC = 0.02

    def __init__(self) -> None:
        super().__init__("joystick_node")

        self._lock = threading.RLock()
        self._selected: Controller | None = None
        self._auto_select: bool = True
        self._gui_signal: Callable[..., None] | None = None
        self._controller_manager = ControllerManager()
        self._pub_joy = self.create_publisher(Joy, "joy", 10)

        # ROS parameter so deadzone can be tuned without editing the node
        self.declare_parameter("deadzone", 0.20)

        @self._controller_manager.event
        def on_connect(controller: Controller) -> None:
            self._on_connect(controller)

        @self._controller_manager.event
        def on_disconnect(controller: Controller) -> None:
            self._on_disconnect(controller)

        self._timer = self.create_timer(
            self.TICK_INTERVAL_SEC, self._timer_callback
        )
        self._try_auto_select_initial()
        self.get_logger().info(
            "Joystick node started (Standard Axes + POV Hat Final Build)"
        )

    def set_gui_signal(self, signal: Callable[..., None]) -> None:
        self._gui_signal = signal

    def get_selected(self) -> dict[str, str] | None:
        with self._lock:
            controller = self._selected
        if controller is None:
            return None
            
        controllers = self._controller_manager.get_controllers()
        idx = controllers.index(controller) if controller in controllers else 0
        return {"name": f"{idx + 1}: {controller.name}", "guid": str(idx)}

    def list_all(self) -> list[dict[str, str]]:
        return [
            {"name": f"{i + 1}: {c.name}", "guid": str(i)}
            for i, c in enumerate(self._controller_manager.get_controllers())
        ]

    def select(self, controller: Controller | str) -> bool:
        resolved = self._resolve_controller(controller)
        if resolved is None:
            return False
        with self._lock:
            self._auto_select = False
        self._assign_controller(resolved)
        return True

    def deselect(self) -> None:
        with self._lock:
            self._selected = None
            self._auto_select = False
        self._emit_controller_changed()

    def destroy_node(self) -> None:
        with self._lock:
            controller = self._selected
            self._selected = None
        if controller is not None:
            try:
                controller.close()
            except Exception:
                pass
        super().destroy_node()

    def _resolve_controller(
            self, controller: Controller | str
        ) -> Controller | None:
            if isinstance(controller, Controller):
                return controller
                
            controllers = self._controller_manager.get_controllers()
            try:
                idx = int(controller)
                return controllers[idx]
            except (ValueError, IndexError):
                return None

    def _try_auto_select_initial(self) -> None:
        if not self._auto_select:
            return
        with self._lock:
            if self._selected is not None:
                return
        controllers = self._controller_manager.get_controllers()
        if not controllers:
            return
        self._assign_controller(controllers[0])

    def _on_connect(self, controller: Controller) -> None:
        self.get_logger().info(
            f"Controller connected: '{controller.name}'"
        )
        with self._lock:
            already_selected = self._selected is not None
            auto = self._auto_select
        if already_selected or not auto:
            return
        self._assign_controller(controller)

    def _on_disconnect(self, controller: Controller) -> None:
        self.get_logger().warn(
            f"Controller disconnected: '{controller.name}'"
        )
        with self._lock:
            is_selected = self._selected is controller
            auto = self._auto_select
        if not is_selected or not auto:
            return
        controllers = self._controller_manager.get_controllers()
        next_controller = controllers[0] if controllers else None
        self._assign_controller(next_controller)

    def _assign_controller(
        self, controller: Controller | None
    ) -> None:
        with self._lock:
            previous = self._selected

        if previous is not None and previous is not controller:
            try:
                previous.close()
            except Exception:
                pass

        if controller is not None:
            controller.open()

        with self._lock:
            self._selected = controller     

        self._emit_controller_changed()

    def _emit_controller_changed(self) -> None:
        if self._gui_signal is None:
            return
        selected = self.get_selected()
        try:
            self._gui_signal(selected)
        except TypeError:
            self._gui_signal()

    def _timer_callback(self) -> None:
        pyglet.app.platform_event_loop.step(0)
        self._send_data()

    def _send_data(self) -> None:
        with self._lock:
            controller = self._selected

        if controller is None:
            return

        try:
            buttons, axes = self._read_controller_data(
                controller,
                self.get_parameter("deadzone").value,
            )
        except Exception as exc:
            self.get_logger().warn(
                f"Controller read failed, deselecting: {exc}"
            )
            with self._lock:
                self._selected = None
            self._emit_controller_changed()
            return

        msg = Joy()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "joy"
        msg.buttons = buttons
        msg.axes = axes
        self._pub_joy.publish(msg)

    def get_deadzone(self) -> float:
            return self.get_parameter("deadzone").value
    
    def set_deadzone(self, value: float) -> None:
        self.set_parameters([Parameter("deadzone", Parameter.Type.DOUBLE, value)])


    def _read_controller_data(self, controller: Controller,deadzone: float,
                              ) -> tuple[list[int], list[float]]:
        
        def apply_deadzone(val: float) -> float:
            return val if abs(val) > deadzone else 0.0

        lx = apply_deadzone(controller.leftx)
        #ly = apply_deadzone(controller.lefty)
        rx = apply_deadzone(controller.rightx)
        ry = apply_deadzone(controller.righty)
        l2 = controller.lefttrigger
        r2 = controller.righttrigger

        throttle = r2 - l2                  # 1 fwd, -1 bwd
        steering = lx                       # 1 right, -1 left 
        camera_vertical = ry                # 1 up, -1 down    
        camera_horizontal = rx              # 1 right, -1 left  
        laser = int(controller.start)       # options button: 1 on, 0 off

        axes = [
            throttle,
            steering,
            camera_vertical,
            camera_horizontal,
        ]
        buttons = [
            laser,
        ]

        return buttons, axes
        