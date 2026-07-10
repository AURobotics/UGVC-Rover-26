from PySide6.QtCore import Signal, QObject, Property, Slot
from console.ros_nodes.worker import ROS2Worker

class Mediator(QObject):
    controller_changed = Signal(object)
    telemetry_updated = Signal()
    auto_change = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.telemetry_exists = False

        self._latitude            = 0.0
        self._longitude           = 0.0
        self._imu_z               = 0.0
        self._linear_vel          = 0.0

        self._battery_1     = 0.0
        self._battery_2     = 0.0
        self._motor_fl      = 0.0
        self._motor_fr      = 0.0
        self._motor_bl      = 0.0
        self._motor_br      = 0.0
        

        self.front_raw_image   = None
        self.rear_raw_image    = None
        #self.face_detect_image = None
        #self.lane_detect_image = None
        #self.video_stream_image = None

        self._current_controller: dict[str, str] | None = None

        self._worker = ROS2Worker()
        
        self._worker.signals.telemetry_received.connect(self.handle_telemetry)

        self._worker.signals.front_received.connect(self.handle_front_image)
        self._worker.signals.rear_received.connect(self.handle_rear_image)
        #self._worker.signals.face_received.connect(self.handle_face_image)
        #self._worker.signals.lane_received.connect(self.handle_lane_image)
        #self._worker.signals.video_received.connect(self.handle_video_image)
        self.auto_change.connect(self._worker.auto_switch)

        self._worker.start()
        self._worker.wait_until_ready()

        joystick = self._worker._joystick_node
        if joystick is not None:
            joystick.set_gui_signal(self.handle_controller_changed)
            self._current_controller = joystick.get_selected()

    @Property(float, notify=telemetry_updated)
    def latitude(self): return self._latitude

    @Property(float, notify=telemetry_updated)
    def longitude(self): return self._longitude

    @Property(float, notify=telemetry_updated)
    def imu_z(self): return self._imu_z

    @Property(float, notify=telemetry_updated)
    def linear_vel(self): return self._linear_vel

    @Property(float, notify=telemetry_updated)
    def battery_1(self): return self._battery_1

    @Property(float, notify=telemetry_updated)
    def battery_2(self): return self._battery_2

    @Property(float, notify=telemetry_updated)
    def motor_fl(self): return self._motor_fl

    @Property(float, notify=telemetry_updated)
    def motor_fr(self): return self._motor_fr

    @Property(float, notify=telemetry_updated)
    def motor_bl(self): return self._motor_bl

    @Property(float, notify=telemetry_updated)
    def motor_br(self): return self._motor_br

    @Property(dict, notify=controller_changed)
    def currentController(self):
        return self._current_controller if self._current_controller else {}

    def set_auto(self, is_auto: bool):
        self.auto_change.emit(is_auto)

    def handle_front_image(self, msg) -> None:
        self.front_raw_image = msg
        self.telemetry_exists = True

    def handle_rear_image(self, msg) -> None:
        self.rear_raw_image = msg
        self.telemetry_exists = True

    #def handle_face_image(self, msg) -> None:
    #    self.face_detect_image = msg
    #    self.telemetry_exists = True
#
    #def handle_lane_image(self, msg) -> None:
    #    self.lane_detect_image = msg
    #    self.telemetry_exists = True
#
    #def handle_video_image(self, msg) -> None:
    #    self.video_stream_image = msg
    #    self.telemetry_exists = True

    def handle_telemetry(self, telemetry: dict) -> None:
        self._latitude            = telemetry.get("latitude",            self._latitude)
        self._longitude           = telemetry.get("longitude",           self._longitude)
        self._imu_z               = telemetry.get("imu_z",               self._imu_z)
        self._linear_vel          = telemetry.get("linear_vel",          self._linear_vel)
        self._battery_1           = telemetry.get("battery_1",           self._battery_1)
        self._battery_2           = telemetry.get("battery_2",           self._battery_2)
        self._motor_fl            = telemetry.get("motor_fl",            self._motor_fl)    
        self._motor_fr            = telemetry.get("motor_fr",            self._motor_fr)
        self._motor_bl            = telemetry.get("motor_bl",            self._motor_bl)
        self._motor_br            = telemetry.get("motor_br",            self._motor_br)
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
    
   # def get_face_frame(self): 
   #     return self.face_detect_image if self.telemetry_exists else None
   # 
   # def get_lane_frame(self): 
   #     return self.lane_detect_image if self.telemetry_exists else None
   # 
   # def get_video_frame(self):
   #     return self.video_stream_image if self.telemetry_exists else None

    def stop(self) -> None:
        if self._worker.isRunning():
            print("Shutting down ROS2 worker thread...")
            self._worker.stop()