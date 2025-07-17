import cv2
import mediapipe as mp
import numpy as np
import time

def AI_sleeep(frame, mp_face_mesh):
    face_mesh = mp_face_mesh.FaceMesh(min_detection_confidence=0.6, min_tracking_confidence=0.6)

    # สร้างสถานะที่จะรีเทิร์น
    final_status = {
        "drowsy": False,
        "yawning": False,
        "microsleep": False
    }

    LEFT_EYE = [33, 160, 158, 133, 153, 144, 145, 23, 24]
    RIGHT_EYE = [362, 385, 387, 263, 373, 380, 374, 253, 254]
    UPPER_LIP = [61, 62, 63, 64, 65, 66]
    LOWER_LIP = [146, 91, 181, 84, 17, 14]

    EAR_BASE_THRESHOLD = 0.25
    yawn_frames = 0
    mar_values = []
    window_size = 10
    MAR_NORMAL = []
    MAR_THRESHOLD = 0.8

    LEFT_IRIS = [474, 475, 476, 477]
    RIGHT_IRIS = [469, 470, 471, 472]

    iris_history = []  # เก็บตำแหน่งลูกตาจากหลายเฟรม
    iris_window_size = 30  # ประมาณ 1-1.5 วินาที (30 เฟรม)
    iris_movement_threshold = 0.005  # ความเปลี่ยนแปลงขั้นต่ำที่ถือว่า "ขยับ"

    def get_iris_center(points, indices):
        coords = np.array([[points[i].x, points[i].y] for i in indices])
        center = np.mean(coords, axis=0)
        return center

    def is_iris_stationary(history, threshold=iris_movement_threshold):
        if len(history) < 2:
            return False
        diffs = [np.linalg.norm(np.array(history[i]) - np.array(history[i-1])) for i in range(1, len(history))]
        avg_movement = np.mean(diffs)
        return avg_movement < threshold

    def calculate_aspect_ratio(points, indices):
        selected_points = np.array([[points[i].x, points[i].y] for i in indices])
        vertical_1 = np.linalg.norm(selected_points[1] - selected_points[5])
        vertical_2 = np.linalg.norm(selected_points[2] - selected_points[4])
        horizontal = np.linalg.norm(selected_points[0] - selected_points[3])

        if horizontal < 0.01:
            return 0.0
        return (vertical_1 + vertical_2) / (2.0 * horizontal)

    def calculate_mouth_aspect_ratio(points):
        upper = np.mean([[points[i].x, points[i].y] for i in UPPER_LIP], axis=0)
        lower = np.mean([[points[i].x, points[i].y] for i in LOWER_LIP], axis=0)

        horizontal = np.linalg.norm(
            np.array([points[78].x, points[78].y]) - np.array([points[308].x, points[308].y])
        )
        vertical = np.linalg.norm(upper - lower)

        if horizontal < 0.01:
            return 0.0
        return vertical / horizontal

    def adjust_ear_threshold(face_width, face_height, base_threshold):
        face_ratio = face_height / face_width if face_width > 0 else 1.0
        adjusted_threshold = base_threshold * (1 + (1 - face_ratio))
        return max(0.15, min(adjusted_threshold, 0.3))

    start_time = time.time()

    frame = cv2.flip(frame, 1)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    face_results = face_mesh.process(rgb_frame)

    annotated_frame = frame.copy()

    if face_results.multi_face_landmarks:
        for face_landmarks in face_results.multi_face_landmarks:
            ih, iw, _ = frame.shape
            face_width = iw
            face_height = ih
            ear_threshold = adjust_ear_threshold(face_width, face_height, EAR_BASE_THRESHOLD)

            for landmark in face_landmarks.landmark:
                x = int(landmark.x * iw)
                y = int(landmark.y * ih)
                cv2.circle(annotated_frame, (x, y), 1, (255, 255, 0), -1)

            try:
                left_ear = calculate_aspect_ratio(face_landmarks.landmark, LEFT_EYE)
                right_ear = calculate_aspect_ratio(face_landmarks.landmark, RIGHT_EYE)
                avg_ear = (left_ear + right_ear) / 2.0

                mar = calculate_mouth_aspect_ratio(face_landmarks.landmark)

                if len(mar_values) >= window_size:
                    mar_values.pop(0)
                mar_values.append(mar)
                smoothed_mar = np.mean(mar_values)

                if len(MAR_NORMAL) < 50:
                    MAR_NORMAL.append(mar)
                else:
                    mean_mar = np.mean(MAR_NORMAL)
                    std_mar = np.std(MAR_NORMAL)
                    MAR_THRESHOLD = mean_mar + 2 * std_mar

                cv2.putText(
                    annotated_frame,
                    f"EAR: {avg_ear:.2f}",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 255, 0),
                    2
                )

                cv2.putText(
                    annotated_frame,
                    f"MAR: {smoothed_mar:.2f}",
                    (10, 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 255, 0),
                    2
                )

                if avg_ear < ear_threshold:
                    final_status["drowsy"] = True
                    cv2.putText(
                        annotated_frame,
                        "DROWSINESS DETECTED!",
                        (10, 70),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 0, 255),
                        2
                    )

                left_iris_center = get_iris_center(face_landmarks.landmark, LEFT_IRIS)
                right_iris_center = get_iris_center(face_landmarks.landmark, RIGHT_IRIS)
                iris_center_avg = ((left_iris_center[0] + right_iris_center[0]) / 2,
                                (left_iris_center[1] + right_iris_center[1]) / 2)

                iris_history.append(iris_center_avg)
                if len(iris_history) > iris_window_size:
                    iris_history.pop(0)

                if is_iris_stationary(iris_history):
                    final_status["microsleep"] = True
                    cv2.putText(
                        annotated_frame,
                        "MICROSLEEP DETECTED!",
                        (10, 130),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 165, 255),  # สีส้ม
                        2
                    )

                if smoothed_mar > MAR_THRESHOLD:
                    final_status["yawning"] = True
                    yawn_frames += 1
                    if yawn_frames > 10:
                        cv2.putText(
                            annotated_frame,
                            "YAWNING DETECTED!",
                            (10, 90),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.5,
                            (255, 0, 255),
                            2
                        )
                else:
                    yawn_frames = 0

            except IndexError:
                print("Index out of range, skipping this face.")

    elapsed_time = time.time() - start_time
    fps = 1 / elapsed_time

    cv2.putText(
        annotated_frame,
        f"FPS: {fps:.2f}",
        (10, 110),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (255, 255, 0),
        2
    )
    # cv2.imshow("Face, Eye & Yawn Detection", annotated_frame)

    face_mesh.close()
    return final_status
