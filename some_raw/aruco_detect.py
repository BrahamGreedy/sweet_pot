import cv2
import time

def main(
    cam_index=0,
    dict_name=cv2.aruco.DICT_4X4_50,
    width=None,
    height=None,
    fps=None,
    draw_rejected=False,
):
    # ArUco detector
    dict_ = cv2.aruco.getPredefinedDictionary(dict_name)
    params = cv2.aruco.DetectorParameters()
    detector = cv2.aruco.ArucoDetector(dict_, params)

    cap = cv2.VideoCapture(cam_index, cv2.CAP_DSHOW)  # CAP_DSHOW helps on Windows
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open camera index={cam_index}")

    # Optional camera settings (not all cameras/drivers respect these)
    if width is not None:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(width))
    if height is not None:
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(height))
    if fps is not None:
        cap.set(cv2.CAP_PROP_FPS, float(fps))

    # Actual settings (what driver gave you)
    real_w = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    real_h = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    real_fps = cap.get(cv2.CAP_PROP_FPS)
    print(f"[Camera] index={cam_index} {real_w:.0f}x{real_h:.0f} fps={real_fps:.2f}")

    last_t = time.time()
    smooth_fps = 0.0

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("Frame grab failed")
                break

            corners, ids, rejected = detector.detectMarkers(frame)
            print(corners)

            if ids is not None and len(ids) > 0:
                cv2.aruco.drawDetectedMarkers(frame, corners, ids)

                # Print ids on frame (sorted for readability)
                ids_list = sorted([int(x) for x in ids.flatten().tolist()])
                cv2.putText(
                    frame,
                    f"ids: {ids_list}",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 0),
                    2,
                    cv2.LINE_AA,
                )
            else:
                cv2.putText(
                    frame,
                    "ids: []",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 0, 255),
                    2,
                    cv2.LINE_AA,
                )

            if draw_rejected and rejected is not None and len(rejected) > 0:
                # Draw rejected candidates in red
                cv2.aruco.drawDetectedMarkers(frame, rejected, borderColor=(0, 0, 255))

            # FPS overlay
            now = time.time()
            inst_fps = 1.0 / max(1e-6, now - last_t)
            last_t = now
            smooth_fps = 0.9 * smooth_fps + 0.1 * inst_fps if smooth_fps > 0 else inst_fps
            cv2.putText(
                frame,
                f"fps: {smooth_fps:.1f}",
                (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )

            cv2.imshow("aruco_detect", frame)

            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord('q')):   # ESC or q
                break

    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    # Examples:
    # main(cam_index=0)
    # main(cam_index=1, width=1280, height=720, fps=30)
    main(cam_index=0, dict_name=cv2.aruco.DICT_4X4_50, width=1280, height=720, fps=30)