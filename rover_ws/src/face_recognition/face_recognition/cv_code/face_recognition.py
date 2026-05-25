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

        # Load feature from cache if it exists, otherwise extract and save it
        self.target_feature = self._load_target()

    def _load_target(self):

        if os.path.exists(FEATURE_CACHE_PATH):
            print(f"[Cache] Loading from cache: {FEATURE_CACHE_PATH}")
            return np.load(FEATURE_CACHE_PATH)

        target_img = cv2.imread(os.path.join(BASE_DIR, "assets", "target.jpg"))

        print("[Cache] No cache found. Extracting feature from 'target.jpg'...")

        if target_img is None:
            raise FileNotFoundError("Could not load 'target.jpg'. Make sure it exists.")

        # Set correct input size for detection
        self.detector.setInputSize((target_img.shape[1], target_img.shape[0]))

        # Detect face in target image
        _, faces = self.detector.detect(target_img)

        if faces is None or len(faces) == 0:
            raise ValueError("No face detected in 'target.jpg'. Please use a clearer image.")

        # Align and crop detected face
        target_face = self.recognizer.alignCrop(target_img, faces[0])

        # Extract 128D feature vector (face embedding)
        feature = self.recognizer.feature(target_face)

        # Save to cache for future runs
        np.save(FEATURE_CACHE_PATH, feature)
        print(f"[Cache] Feature saved to '{FEATURE_CACHE_PATH}'. Future runs will load instantly.")

        return feature

    def recognize_frame(self, frame):

        start_time = time.time()

        # Update detector with frame size
        self.detector.setInputSize((frame.shape[1], frame.shape[0]))

        # Detect faces in current frame
        _, faces = self.detector.detect(frame)

        if faces is not None:

            for face in faces:

                # Align face
                aligned_face = self.recognizer.alignCrop(frame, face)

                # Extract features
                feature = self.recognizer.feature(aligned_face)

                # Compare with target face
                score = self.recognizer.match(
                    self.target_feature,
                    feature,
                    cv2.FaceRecognizerSF_FR_COSINE
                )

                # Get bounding box
                x, y, w, h = map(int, face[:4])

                # Decide if same person
                if score > 0.45:
                    label = "MATCH"
                    color = (0, 255, 0)
                else:
                    label = "UNKNOWN"
                    color = (0, 0, 255)

                # Measure processing time
                processing_time = time.time() - start_time

                # Draw rectangle
                cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)

                # Show result text
                cv2.putText(
                    frame,
                    f"{label} {score:.2f} {processing_time:.3f}s",
                    (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    color,
                    2
                )

        return frame

def main():

    # Start webcam
    cap = cv2.VideoCapture(0)

    face_recognition = FaceRecognition()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = face_recognition.recognize_frame(frame)
        cv2.imshow("Face Recognition", frame)

        # Press ESC to exit
        if cv2.waitKey(1) == 27:
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()