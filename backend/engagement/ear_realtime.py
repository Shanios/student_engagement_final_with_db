import cv2
import mediapipe as mp
import numpy as np
import math

mp_face_mesh = mp.solutions.face_mesh

# Eye landmark indices
LEFT_EYE_IDX = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_IDX = [263, 387, 385, 362, 380, 373]

def euclidean_dist(p1, p2):
    return math.dist(p1, p2)

def eye_aspect_ratio(eye_pts):
    p1, p2, p3, p4, p5, p6 = eye_pts
    dist_v1 = euclidean_dist(p2, p6)
    dist_v2 = euclidean_dist(p3, p5)
    dist_h = euclidean_dist(p1, p4)
    return (dist_v1 + dist_v2) / (2.0 * dist_h)

def get_eye_points(landmarks, indices, w, h):
    pts = []
    for idx in indices:
        lm = landmarks[idx]
        pts.append((int(lm.x * w), int(lm.y * h)))
    return pts

cap = cv2.VideoCapture(0)

with mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
) as face_mesh:

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb)

        if results.multi_face_landmarks:
            face_lm = results.multi_face_landmarks[0].landmark

            left_eye = get_eye_points(face_lm, LEFT_EYE_IDX, w, h)
            right_eye = get_eye_points(face_lm, RIGHT_EYE_IDX, w, h)

            left_ear = eye_aspect_ratio(left_eye)
            right_ear = eye_aspect_ratio(right_eye)
            ear_avg = (left_ear + right_ear) / 2.0

            # Draw eye points
            for (x, y) in left_eye + right_eye:
                cv2.circle(frame, (x, y), 2, (255, 255, 255), -1)

            # Show EAR
            cv2.putText(frame, f"EAR: {ear_avg:.3f}", (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        cv2.imshow("EAR Model", frame)
        if cv2.waitKey(1) & 0xFF == 27:  
            break

cap.release()
cv2.destroyAllWindows()
