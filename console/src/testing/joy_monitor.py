#! /usr/bin/env python3
"""Print /joy in human-readable form. Run while `pixi run console` is active."""

from __future__ import annotations

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy

BUTTON_LABELS = (
    "A",       # Cross
    "B",       # Circle
    "X",       # Square
    "Y",       # Triangle
    "LB",      # L1
    "RB",      # R1
    "Start",   # Options
    "Back",    # Create
    "Guide",   # PS button
    "L3",
    "R3",
    "DPAD_L",  # Index 11 -> d_x < 0
    "DPAD_R",  # Index 12 -> d_x > 0
    "DPAD_U",  # Index 13 -> d_y > 0
    "DPAD_D",  # Index 14 -> d_y < 0
)
AXIS_LABELS = ("LX", "LY", "RX", "RY", "L2", "R2")


class JoyMonitor(Node):
    def __init__(self) -> None:
        super().__init__("joy_monitor")
        self._last_buttons: list[int] = []
        self._last_axes: list[float] = []
        self.create_subscription(Joy, "joy", self._on_joy, 10)
        self.get_logger().info(
            "Watching /joy — press buttons and move sticks (Ctrl+C to stop)"
        )

    def _on_joy(self, msg: Joy) -> None:
        buttons = list(msg.buttons)
        axes = [round(v, 2) for v in msg.axes]

        if buttons == self._last_buttons and axes == self._last_axes:
            return

        self._last_buttons = buttons
        self._last_axes = axes

        pressed = [
            BUTTON_LABELS[i]
            for i, v in enumerate(buttons)
            if v and i < len(BUTTON_LABELS)
        ]
        active_axes = [
            f"{AXIS_LABELS[i]}={axes[i]}"
            for i in range(min(len(axes), len(AXIS_LABELS)))
            if abs(axes[i]) > 0.05
        ]

        print("---")
        print(f"buttons ({len(buttons)}): pressed={pressed or '(none)'}")
        print(f"axes ({len(axes)}): {', '.join(active_axes) or '(idle)'}")


def main() -> None:
    rclpy.init()
    node = JoyMonitor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
