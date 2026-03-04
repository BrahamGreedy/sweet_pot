import cv2
import numpy as np

ALLOWED_IDS = set([0, 1, 2, 3, 4])  # допустимые id

def my_filled_circle(img, center, r):  # точка-центр
    return cv2.circle(img, center, r, (0, 0, 255), -1, 8)

def marker_center(corners_4x2: np.ndarray) -> np.ndarray:
    """
    corners_4x2: (4,2) float
    return: (2,) float center
    """
    return corners_4x2.mean(axis=0)

def main():
    dict_ = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    params = cv2.aruco.DetectorParameters()
    detector = cv2.aruco.ArucoDetector(dict_, params)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Cannot open camera index=0")

    while True:
        ok, frame = cap.read()
        if not ok:
            print("Frame grab failed")
            break

        corners, ids, _ = detector.detectMarkers(frame)

        crop_masked = None

        if ids is not None and len(ids) > 0:
            # ids: (N,1) -> (N,)
            ids_flat = ids.flatten()

            # отбираем только нужные id (0..4)
            centers = []
            used_ids = []
            for i, mid in enumerate(ids_flat):
                if int(mid) in ALLOWED_IDS:
                    c = corners[i].reshape(4, 2).astype(np.float32)
                    centers.append(marker_center(c))
                    used_ids.append(int(mid))

            # рисуем найденные маркеры и их центры
            if len(centers) > 0:
                cv2.aruco.drawDetectedMarkers(frame, corners, ids)
                for p in centers:
                    frame = my_filled_circle(frame, (int(p[0]), int(p[1])), 5)

            # делаем кроп/маску только если маркеров 4 или 5 (как ты просил)
            if len(centers) >= 4:
                pts = np.array(centers, dtype=np.float32)  # (M,2)

                # 1) "обводка" центров: выпуклая оболочка
                hull = cv2.convexHull(pts)  # (K,1,2) float32

                # 2) опоясывающий прямоугольник (ось X/Y, без поворота)
                x, y, w, h = cv2.boundingRect(hull.astype(np.int32))

                # небольшая "подушка", чтобы маркеры не прилипали к краю
                pad = 10
                x2 = max(0, x - pad)
                y2 = max(0, y - pad)
                x3 = min(frame.shape[1], x + w + pad)
                y3 = min(frame.shape[0], y + h + pad)

                crop = frame[y2:y3, x2:x3].copy()

                # 3) маска: всё вне "поля" (вне hull) делаем чёрным
                mask = np.zeros((crop.shape[0], crop.shape[1]), dtype=np.uint8)

                # смещаем hull в координаты кропа
                hull_shifted = hull.copy()
                hull_shifted[:, 0, 0] -= x2
                hull_shifted[:, 0, 1] -= y2
                hull_shifted_i = hull_shifted.astype(np.int32)

                cv2.fillPoly(mask, [hull_shifted_i], 255)

                # применяем маску (вне hull станет 0 -> чёрным)
                crop_masked = cv2.bitwise_and(crop, crop, mask=mask)

                # (необязательно) нарисуем контур в окне кропа
                cv2.polylines(crop_masked, [hull_shifted_i], True, (0, 255, 0), 2)

                # (необязательно) подпись id-шников
                cv2.putText(
                    crop_masked,
                    f"IDs: {sorted(used_ids)}",
                    (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 255, 255),
                    2,
                    cv2.LINE_AA,
                )

        cv2.imshow("aruco_detect", frame)
        if crop_masked is not None:
            cv2.imshow("crop_masked", crop_masked)

        key = cv2.waitKey(1) & 0xFF
        if key in (27, ord('q')):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()