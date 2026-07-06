from PySide6.QtCore import Signal, QObject, Property, Slot
from console.ros_nodes.worker import ROS2Worker

class Mediator(QObject):
    controller_changed = Signal()
    telemetry_updated = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.telemetry_exists = False

        self._status_state        = "Unknown"
        self._latitude            = 0.0
        self._longitude           = 0.0
        self._battery_voltage     = 0.0
        self._left_motor_voltage  = 0.0
        self._right_motor_voltage = 0.0
        self._battery_percent     = 0.0
        self._imu_accel_z         = 0.0

        self.front_raw_image   = None
        self.rear_raw_image    = None
        self.face_detect_image = None
        self.lane_detect_image = None
        self.video_stream_image = None

        self._current_controller: dict[str, str] | None = None

        self._worker = ROS2Worker()
        
        self._worker.signals.telemetry_received.connect(self.handle_telemetry)

        self._worker.signals.front_received.connect(self.handle_front_image)
        self._worker.signals.rear_received.connect(self.handle_rear_image)
        self._worker.signals.face_received.connect(self.handle_face_image)
        self._worker.signals.lane_received.connect(self.handle_lane_image)
        self._worker.signals.video_received.connect(self.handle_video_image)

        self._worker.start()
        self._worker.wait_until_ready()

        joystick = self._worker._joystick_node
        if joystick is not None:
            joystick.set_gui_signal(self.handle_controller_changed)
            self._current_controller = joystick.get_selected()

    @Property(str, notify=telemetry_updated)
    def statusState(self): return self._status_state

    @Property(float, notify=telemetry_updated)
    def latitude(self): return self._latitude

    @Property(float, notify=telemetry_updated)
    def longitude(self): return self._longitude

    @Property(float, notify=telemetry_updated)
    def batteryVoltage(self): return self._battery_voltage

    @Property(float, notify=telemetry_updated)
    def leftMotorVoltage(self): return self._left_motor_voltage

    @Property(float, notify=telemetry_updated)
    def rightMotorVoltage(self): return self._right_motor_voltage

    @Property(float, notify=telemetry_updated)
    def batteryPercent(self): return self._battery_percent

    @Property(float, notify=telemetry_updated)
    def imuAccelZ(self): return self._imu_accel_z

    @Property(dict, notify=controller_changed)
    def currentController(self):
        return self._current_controller if self._current_controller else {}


    def handle_front_image(self, msg) -> None:
        self.front_raw_image = msg
        self.telemetry_exists = True

    def handle_rear_image(self, msg) -> None:
        self.rear_raw_image = msg
        self.telemetry_exists = True

    def handle_face_image(self, msg) -> None:
        self.face_detect_image = msg
        self.telemetry_exists = True

    def handle_lane_image(self, msg) -> None:
        self.lane_detect_image = msg
        self.telemetry_exists = True

    def handle_video_image(self, msg) -> None:
        self.video_stream_image = msg
        self.telemetry_exists = True

    def handle_telemetry(self, telemetry: dict) -> None:
        self._status_state        = telemetry.get("status_state",        self._status_state)
        self._latitude            = telemetry.get("latitude",            self._latitude)
        self._longitude           = telemetry.get("longitude",           self._longitude)
        self._battery_voltage     = telemetry.get("battery_voltage",     self._battery_voltage)
        self._left_motor_voltage  = telemetry.get("left_motor_voltage",  self._left_motor_voltage)
        self._right_motor_voltage = telemetry.get("right_motor_voltage", self._right_motor_voltage)
        self._battery_percent     = telemetry.get("battery_percent",     self._battery_percent)
        self._imu_accel_z         = telemetry.get("imu_accel_z",         self._imu_accel_z)
        self.telemetry_exists = True
        self.telemetry_updated.emit()

    def handle_controller_changed(self, controller_info: dict[str, str] | None) -> None:
        self._current_controller = controller_info
        self.controller_changed.emit(controller_info)

    def get_active_controller(self) -> dict[str, str] | None:
        return self._current_controller

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

    def refresh(self):
        if self._worker and self._worker._joystick_node:
            self._worker._joystick_node.refresh() 

    def get_frame(self): 
        return self.front_raw_image if self.telemetry_exists else None
    
    def get_rear_frame(self):
        return self.rear_raw_image if self.telemetry_exists else None
    
    def get_face_frame(self): 
        return self.face_detect_image if self.telemetry_exists else None
    
    def get_lane_frame(self): 
        return self.lane_detect_image if self.telemetry_exists else None
    
    def get_video_frame(self):
        return self.video_stream_image if self.telemetry_exists else None

    def stop(self) -> None:
        if self._worker.isRunning():
            print("Shutting down ROS2 worker thread...")
            self._worker.stop()