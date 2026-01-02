import cv2
import mediapipe as mp
import numpy as np
import math
import csv
import time

# ---------- CONFIG ----------
CSV_PATH = "ear_dataset.csv"   # output file name
EAR_THRESHOLD_VISUAL = 0.19    # just for your own reference (not used for label)
# -----------------------------

mp_face_mesh = mp.solutions.face_mesh

# MediaPipe landmark indices for eyes (approx, works well enough)
# Left eye (from viewer's perspective)
LEFT_EYE_IDX = [33, 160, 158, 133, 153, 144]
# Right eye
RIGHT_EYE_IDX = [263, 387, 385, 362, 380, 373]


def euclidean_dist(p1, p2):
    return math.dist(p1, p2)


def eye_aspect_ratio(eye_points):
    """
    eye_points = [P1, P2, P3, P4, P5, P6]
    where:
    P1, P4 -> horizontal corners
    P2, P3 -> upper eyelid points
    P5, P6 -> lower eyelid points
    """
    p1, p2, p3, p4, p5, p6 = eye_points

    dist_v1 = euclidean_dist(p2, p6)
    dist_v2 = euclidean_dist(p3, p5)
    dist_h = euclidean_dist(p1, p4)

    ear = (dist_v1 + dist_v2) / (2.0 * dist_h)
    return ear


def get_eye_points(landmarks, indices, img_w, img_h):
    pts = []
    for idx in indices:
        lm = landmarks[idx]
        x, y = int(lm.x * img_w), int(lm.y * img_h)
        pts.append((x, y))
    return pts


def main():
    cap = cv2.VideoCapture(0)

    # Open CSV file and prepare writer
    csv_file = open(CSV_PATH, mode="w", newline="")
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow(["timestamp", "ear", "label"])  # header row

    current_label = None  # "engaged", "not_engaged", or None

    print("Controls:")
    print("  E -> label = engaged")
    print("  N -> label = not_engaged")
    print("  U -> unlabeled (pause logging)")
    print("  Q or ESC -> quit")

    with mp_face_mesh.FaceMesh(
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    ) as face_mesh:

        while True:
            ret, frame = cap.read()
            if not ret:
                print("Failed to read from camera.")
                break

            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_mesh.process(rgb)

            ear_avg = None

            if results.multi_face_landmarks:
                face_landmarks = results.multi_face_landmarks[0].landmark

                left_eye_pts = get_eye_points(face_landmarks, LEFT_EYE_IDX, w, h)
                right_eye_pts = get_eye_points(face_landmarks, RIGHT_EYE_IDX, w, h)

                left_ear = eye_aspect_ratio(left_eye_pts)
                right_ear = eye_aspect_ratio(right_eye_pts)
                ear_avg = (left_ear + right_ear) / 2.0

                # Draw eye points
                for (x, y) in left_eye_pts + right_eye_pts:
                    cv2.circle(frame, (x, y), 2, (255, 255, 255), -1)

                # Show EAR value
                cv2.putText(frame, f"EAR: {ear_avg:.3f}", (20, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

                # Just a visual line to see approximate threshold
                cv2.putText(frame, f"Ref Thr: {EAR_THRESHOLD_VISUAL:.2f}", (20, 80),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

                # If we have a current label, log this frame to CSV
                if current_label is not None:
                    ts = time.time()
                    csv_writer.writerow([ts, ear_avg, current_label])

            # Show current label on screen
            label_text = f"Label: {current_label if current_label else 'None'}"
            cv2.putText(frame, label_text, (20, 120),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

            cv2.imshow("EAR Data Collection", frame)

            key = cv2.waitKey(1) & 0xFF

            if key == ord('e'):
                current_label = "engaged"
                print("Label set to: engaged")
            elif key == ord('n'):
                current_label = "not_engaged"
                print("Label set to: not_engaged")
            elif key == ord('u'):
                current_label = None
                print("Label set to: None (pause logging)")
            elif key == ord('q') or key == 27:  # 'q' or ESC
                print("Quitting...")
                break

    cap.release()
    cv2.destroyAllWindows()
    csv_file.close()
    print(f"Saved data to {CSV_PATH}")


if __name__ == "__main__":
    main()
