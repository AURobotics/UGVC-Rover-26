from PySide6.QtWidgets import QWidget, QLabel, QComboBox
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import Slot, QTimer
from sensor_msgs.msg import CompressedImage
from cv_bridge import CvBridge #converts ros2 img to numpy array
from console.ros_nodes.mediator import Mediator

class CameraDisplay(QWidget):

    def __init__(self, mediator: Mediator, parent=None):
        super().__init__(parent)
        self._aspect_ratio = 4 / 3
        self._bridge = CvBridge()
        self.mediator = mediator

        self._frame_view = QLabel(self)
        self._frame_view.setScaledContents(True)

        self._cam_select = QComboBox(self)
        self._cam_select.setStyleSheet("background-color: black;")
        #self._cam_select.addItem('Test Camera', self.mediator.get_video_frame)
        self._cam_select.addItem('Front Camera', self.mediator.get_frame)
        self._cam_select.addItem('Rear Camera', self.mediator.get_rear_frame)
        #self._cam_select.addItem('Face Detection', self.mediator.get_face_frame)
        #self._cam_select.addItem('Lane Detection', self.mediator.get_lane_frame)
        self._cam_select.currentIndexChanged.connect(self._on_camera_changed)

        self._frame_getter = self.mediator.get_video_frame  # Default to front camera
        self._cam_select.setCurrentIndex(0)  # Set default selection to front Camera

        self._cam_timer = QTimer()
        self._cam_timer.timeout.connect(self._update_camera_display)
        self._cam_timer.setInterval(33)  # Approximately 30 FPS
        self._cam_timer.start()

    @Slot(object)
    def update_frame(self, msg: CompressedImage):
        """Call this with a ROS CompressedImage message to update the display."""
        frame = self._bridge.compressed_imgmsg_to_cv2(msg, desired_encoding='bgr8')
        if frame is not None:
            image = QImage(
                frame.data,
                frame.shape[1], frame.shape[0], #width, height
                frame.strides[0], #bytes per line
                QImage.Format.Format_BGR888
            )
            self._frame_view.setPixmap(QPixmap.fromImage(image))

    def _update_camera_display(self):
        frame = self._frame_getter()
        if frame is not None:
            self.update_frame(frame)

    def _on_camera_changed(self, index):
        self._frame_getter = self._cam_select.itemData(index)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w, h = self.width(), self.height()
        if w > h * self._aspect_ratio:
            nw, nh = int(h * self._aspect_ratio), h
        else:
            nw, nh = w, int(w / self._aspect_ratio)
        self._frame_view.setGeometry((w - nw) // 2, (h - nh) // 2, nw, nh)
        self._cam_select.move((w - nw) // 2 + 10, (h + nh) // 2 - self._cam_select.height() - 10)

    def hideEvent(self, event):
        super().hideEvent(event)
        self._cam_timer.stop()

    def showEvent(self, event):
        super().showEvent(event)
        self._cam_timer.start()