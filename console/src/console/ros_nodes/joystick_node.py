#! /usr/bin/env python3
import threading
from collections.abc import Callable

import pyglet
import pyglet.window
from pyglet.input import Controller, ControllerManager
from rclpy.node import Node
from sensor_msgs.msg import Joy


class JoystickNode(Node):
    TICK_INTERVAL_SEC = 0.02  # 50 Hz

    def __init__(self) -> None:
        super().__init__("joystick_node")

        # ── shared state ────────────────────────────────────────────────
        self._lock = threading.RLock()
        self._selected: Controller | None = None
        self._auto_select: bool = True
        self._gui_signal: Callable[..., None] | None = None
        self._controller_manager = ControllerManager()
        self._pub_joy = self.create_publisher(Joy, "joy", 10)

        @self._controller_manager.event
        def on_connect(controller: Controller) -> None:
            self._on_connect(controller)

        @self._controller_manager.event
        def on_disconnect(controller: Controller) -> None:
            self._on_disconnect(controller)

        self._timer = self.create_timer(self.TICK_INTERVAL_SEC, self._timer_callback)
        self._try_auto_select_initial()
    # ── Public API (gui_thread panel) ────────────────────────────────────

    def set_gui_signal(self, signal: Callable[..., None]) -> None:
        self._gui_signal = signal

    def get_selected(self) -> dict[str, str] | None:
        with self._lock:
            controller = self._selected
        if controller is None:
            return None
        return {"name": controller.name, "guid": controller.guid}

    def list_all(self) -> list[dict[str, str]]:
        return [
            {"name": c.name, "guid": c.guid}
            for c in self._controller_manager.get_controllers()
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

    # Internal helpers

    def _resolve_controller(self, controller: Controller | str) -> Controller | None:
        if isinstance(controller, Controller):
            return controller
        for candidate in self._controller_manager.get_controllers():
            if candidate.guid == controller:
                return candidate
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
        with self._lock:
            already_selected = self._selected is not None
            auto = self._auto_select
        if already_selected or not auto:
            return
        self._assign_controller(controller)

    def _on_disconnect(self, controller: Controller) -> None:
        with self._lock:
            is_selected = self._selected is controller
            auto = self._auto_select
        if not is_selected or not auto:
            return

        controllers = self._controller_manager.get_controllers()
        next_controller = controllers[0] if controllers else None
        self._assign_controller(next_controller)

    def _assign_controller(self, controller: Controller | None) -> None:
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

    # Timer: pyglet tick → send data 

    def _timer_callback(self) -> None:
        pyglet.app.platform_event_loop.step(0)
        self._send_data()

    def _send_data(self) -> None:
        with self._lock:
            controller = self._selected

        if controller is None:
            return

        try:
            buttons, axes = self._read_controller_data(controller)
        except Exception as exc:
            self.get_logger().warn(f"Controller read failed, deselecting: {exc}")
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


    @staticmethod
    def _read_controller_data(controller: Controller) -> tuple[list[int], list[float]]:
        buttons = [
            int(controller.a),              #  0  Cross
            int(controller.b),              #  1  Circle
            int(controller.x),              #  2  Square
            int(controller.y),              #  3  Triangle
            int(controller.leftshoulder),   #  4  L1
            int(controller.rightshoulder),  #  5  R1
            int(controller.start),          #  6  Options
            int(controller.back),           #  7  Create
            int(controller.guide),          #  8  PS button
            int(controller.leftthumb),      #  9  L3
            int(controller.rightthumb),     # 10  R3
            0,                              # 11  D-pad Up 
            0,                              # 12  D-pad Down
            0,                              # 13  D-pad Left
            0,                              # 14  D-pad Right
        ]

        axes = [
            float(controller.leftstick.x),   # 0  Left stick X
            float(controller.leftstick.y),   # 1  Left stick Y
            float(controller.rightstick.x),  # 2  Right stick X
            float(controller.rightstick.y),  # 3  Right stick Y
            float(controller.lefttrigger),   # 4  L2
            float(controller.righttrigger),  # 5  R2
        ]

        return buttons, axes