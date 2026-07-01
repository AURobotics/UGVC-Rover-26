import cv2
import time
import numpy as np
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FEATURE_CACHE_PATH = os.path.join(BASE_DIR, "target_feature.npy")

class FaceRecognition:
    def __init__(self):
        self.detector = cv2.FaceDetectorYN.create(
            os.path.join(BASE_DIR, "face_detection_yunet_2023mar.onnx"),
            "",
            (640, 480)
        )
        self.recognizer = cv2.FaceRecognizerSF.create(
            os.path.join(BASE_DIR, "face_recognition_sface_2021dec.onnx"),
            ""
        )
        self.target_feature = self._load_target()

    def _load_target(self):
        if os.path.exists(FEATURE_CACHE_PATH):
            print(f"[Cache] Loading from cache: {FEATURE_CACHE_PATH}")
            return np.load(FEATURE_CACHE_PATH)

        target_img = cv2.imread(os.path.join(BASE_DIR, "assets", "target.jpg"))
        print("[Cache] No cache found. Extracting feature from 'target.jpg'...")

        if target_img is None:
            raise FileNotFoundError("Could not load 'target.jpg'. Make sure it exists.")

        self.detector.setInputSize((target_img.shape[1], target_img.shape[0]))
        _, faces = self.detector.detect(target_img)

        if faces is None or len(faces) == 0:
            raise ValueError("No face detected in 'target.jpg'. Please use a clearer image.")

        target_face = self.recognizer.alignCrop(target_img, faces[0])
        feature = self.recognizer.feature(target_face)
        np.save(FEATURE_CACHE_PATH, feature)
        print(f"[Cache] Feature saved to '{FEATURE_CACHE_PATH}'. Future runs will load instantly.")

        return feature

    def recognize_frame(self, frame):
        start_time = time.time()

        self.detector.setInputSize((frame.shape[1], frame.shape[0]))
        _, faces = self.detector.detect(frame)

        is_faces = faces is not None
        is_detected = False
        offset_x = None  # percentage float, e.g. -42.5
        offset_y = None  # percentage float, e.g. 10.3

        if faces is not None:
            for face in faces:
                aligned_face = self.recognizer.alignCrop(frame, face)
                feature = self.recognizer.feature(aligned_face)
                score = self.recognizer.match(
                    self.target_feature,
                    feature,
                    cv2.FaceRecognizerSF_FR_COSINE
                )

                x, y, w, h = map(int, face[:4])
                processing_time = time.time() - start_time

                if score > 0.45:
                    label = "MATCH"
                    color = (0, 255, 0)
                    is_detected = True
                    offset_x, offset_y = self.get_offset_percent(face, frame)  # returns (float, float)
                else:
                    label = "UNKNOWN"
                    color = (0, 0, 255)

                cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                cv2.putText(
                    frame,
                    f"{label} {score:.2f} {processing_time:.3f}s",
                    (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    color,
                    2
                )

        return frame, is_faces, is_detected, offset_x, offset_y

    def get_offset_percent(self, face, frame):
        frame_height, frame_width = frame.shape[:2]
        x, y, w, h = map(int, face[:4])

        face_center_x = x + w / 2
        face_center_y = y + h / 2

        offset_x_pct = (face_center_x - frame_width / 2) / (frame_width / 2) * 100
        offset_y_pct = (face_center_y - frame_height / 2) / (frame_height / 2) * 100

        return float(offset_x_pct), float(offset_y_pct)


def main():
    cap = cv2.VideoCapture(0)
    face_recognition = FaceRecognition()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame, is_faces, is_detected, offset_x, offset_y = face_recognition.recognize_frame(frame)
        print(f"Faces Detected: {is_faces} | Target Detected: {is_detected} | Offset X: {offset_x}% | Offset Y: {offset_y}%")
        cv2.imshow("Face Recognition", frame)

        if cv2.waitKey(1) == 27:
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()