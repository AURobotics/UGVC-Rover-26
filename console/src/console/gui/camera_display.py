from PySide6.QtWidgets import QWidget, QLabel
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import Slot
from sensor_msgs.msg import CompressedImage
from cv_bridge import CvBridge #converts ros2 img to numpy array

class CameraDisplay(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._aspect_ratio = 4 / 3
        self._bridge = CvBridge()

        self._frame_view = QLabel(self)
        self._frame_view.setScaledContents(True)

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

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w, h = self.width(), self.height()
        if w > h * self._aspect_ratio:
            nw, nh = int(h * self._aspect_ratio), h
        else:
            nw, nh = w, int(w / self._aspect_ratio)
        self._frame_view.setGeometry((w - nw) // 2, (h - nh) // 2, nw, nh)