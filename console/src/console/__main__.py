import sys
from PySide6.QtCore import QCoreApplication
from console.ros_nodes.worker import ROS2Worker


def main() -> None:
    app = QCoreApplication(sys.argv)
    worker = ROS2Worker()
    print(" Standalone ROS 2 Worker Started! Waiting for Joystick...")
    worker.start()

    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        print("\n Shutting down Worker...")
        worker.stop()


if __name__ == "__main__":
    main()
