#! /usr/bin/env python3
import threading
from collections.abc import Callable

import pyglet
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
        self.declare_parameter("deadzone", 0.15)

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

    def _resolve_controller(
        self, controller: Controller | str
    ) -> Controller | None:
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


################ MN AI TOOL ################
    def _read_controller_data(
        self,
        controller: Controller,
        deadzone: float,
    ) -> tuple[list[int], list[float]]:
        raw_axes = [0.0] * 6

        # absolute_axis_controls is an internal pyglet attribute — guard in
        # case it disappears in a future pyglet version
        if hasattr(controller, "absolute_axis_controls"):
            for i, axis in enumerate(controller.absolute_axis_controls):
                if i < 6 and axis and axis.value is not None:
                    raw_axes[i] = float(axis.value)
        else:
            self.get_logger().warn(
                "Controller has no 'absolute_axis_controls' — axes will read 0. "
                "Check your pyglet version.",
                throttle_duration_sec=5.0,
            )

        def normalize_stick(raw_val: float) -> float:
            return max(-1.0, min(1.0, (raw_val - 32768.0) / 32768.0))

        def normalize_trigger(raw_val: float) -> float:
            return max(0.0, min(1.0, raw_val / 65535.0))

        lx = normalize_stick(raw_axes[0])
        ly = normalize_stick(raw_axes[1])
        rx = normalize_stick(raw_axes[2])
        ry = -normalize_stick(raw_axes[3])  # negated: hardware axis is inverted
        l2 = normalize_trigger(raw_axes[4])
        r2 = normalize_trigger(raw_axes[5])

        buttons = [
            int(controller.a),              # 0  Cross
            int(controller.b),              # 1  Circle
            int(controller.x),              # 2  Square
            int(controller.y),              # 3  Triangle
            int(controller.leftshoulder),   # 4  L1
            int(controller.rightshoulder),  # 5  R1
            int(controller.leftthumb),      # 6  L3
            int(controller.rightthumb),     # 7  R3
            int(controller.start),          # 8  Options
            int(controller.back),           # 9  Create/ Share
            int(controller.guide),          # 10 PS button
            int(controller.dpad.x == -1),   # 11 dpad-left
            int(controller.dpad.x == 1),    # 12 dpad-right
            int(controller.dpad.y == -1),   # 13 dpad-down
            int(controller.dpad.y == 1)     # 14 dpad-up
            
            
        ]

        def apply_deadzone(val: float) -> float:
            return val if abs(val) > deadzone else 0.0

        axes = [
            apply_deadzone(lx),  # 0  Left stick X
            apply_deadzone(ly),  # 1  Left stick Y
            apply_deadzone(rx),  # 2  Right stick X
            apply_deadzone(ry),  # 3  Right stick Y
            l2,                  # 4  L2  [0.0 → 1.0]
            r2,                  # 5  R2  [0.0 → 1.0]
        ]

        return buttons, axes