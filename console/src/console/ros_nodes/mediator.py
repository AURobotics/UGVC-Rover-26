#! /usr/bin/env python3
from PySide6.QtCore import Signal, QObject
from console.ros_nodes.worker import ROS2Worker

class Mediator(QObject):
    controller_changed = Signal(object)

    def __init__(self, parent=None):
        super().__init__()
        self.telemetry_exists = False

        self.status_state        = "Unknown"
        self.latitude            = 0.0
        self.longitude           = 0.0
        self.battery_voltage     = 0.0
        self.left_motor_voltage  = 0.0
        self.right_motor_voltage = 0.0
        self.battery_percent     = 0.0
        self.imu_accel_z         = 0.0

        self.front_raw_image   = None
        self.rear_raw_image    = None
        self.face_detect_image = None
        self.lane_detect_image = None
        ############
        self.video_stream_image = None

        self.current_controller: dict[str, str] | None = None

        self._worker = ROS2Worker()
        self._worker.signals.telemetry_received.connect(self.handle_telemetry)
        self._worker.start()

        self._worker.wait_until_ready()

        joystick = self._worker._joystick_node
        if joystick is not None:
            joystick.set_gui_signal(self.handle_controller_changed)
            self.current_controller = joystick.get_selected()

    def handle_telemetry(self, telemetry: dict) -> None:
        self.status_state        = telemetry.get("status_state",        self.status_state)
        self.latitude            = telemetry.get("latitude",            self.latitude)
        self.longitude           = telemetry.get("longitude",           self.longitude)
        self.battery_voltage     = telemetry.get("battery_voltage",     self.battery_voltage)
        self.left_motor_voltage  = telemetry.get("left_motor_voltage",  self.left_motor_voltage)
        self.right_motor_voltage = telemetry.get("right_motor_voltage", self.right_motor_voltage)
        self.battery_percent     = telemetry.get("battery_percent",     self.battery_percent)
        self.imu_accel_z         = telemetry.get("imu_accel_z",         self.imu_accel_z)

        front = telemetry.get("front_raw_image")
        if front is not None:
            self.front_raw_image = front
        rear = telemetry.get("rear_raw_image")
        if rear is not None:
            self.rear_raw_image = rear
        face = telemetry.get("face_detect_image")
        if face is not None:
            self.face_detect_image = face
        lane = telemetry.get("lane_detect_image")
        if lane is not None:
            self.lane_detect_image = lane
            
        ###############
        video = telemetry.get("video_stream_image")
        if video is not None:
            self.video_stream_image = video

        self.telemetry_exists = True

    def handle_controller_changed(self, controller_info: dict[str, str] | None) -> None:
        self.current_controller = controller_info
        self.controller_changed.emit(controller_info)

    def get_active_controller(self) -> dict[str, str] | None:
        return self.current_controller

    def get_available_controllers(self) -> list[dict[str, str]]:
        joystick = self._worker._joystick_node
        if joystick is not None:
            return joystick.list_all()
        return []

    def select_controller_by_guid(self, guid: str) -> bool:
        joystick = self._worker._joystick_node
        if joystick is not None:
            return joystick.select(guid)
        return False

    def deselect_active_controller(self) -> None:
        joystick = self._worker._joystick_node
        if joystick is not None:
            joystick.deselect()

    def get_joystick_deadzone(self) -> float:
        joystick = self._worker._joystick_node
        if joystick is not None:
            return joystick.get_deadzone()
        return 0.20

    def set_joystick_deadzone(self, value: float) -> None:
        joystick = self._worker._joystick_node
        if joystick is not None:
            joystick.set_deadzone(value)

    def get_frame(self):
        return self.front_raw_image if self.telemetry_exists else None

    def get_rear_frame(self):
        return self.rear_raw_image if self.telemetry_exists else None

    def get_face_frame(self):
        return self.face_detect_image if self.telemetry_exists else None

    def get_lane_frame(self):
        return self.lane_detect_image if self.telemetry_exists else None

    ##############
    def get_video_frame(self):
        return self.video_stream_image if self.telemetry_exists else None

    def stop(self) -> None:
        if self._worker.isRunning():
            print("Shutting down ROS2 worker thread...")
            self._worker.stop()