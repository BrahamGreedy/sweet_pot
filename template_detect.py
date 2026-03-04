import cv2
import time

def my_filled_circle(img, center, r): #функция для отрисовки точки
    thickness = -1
    line_type = 8
 
    return cv2.circle(img,
               center,
               r,
               (0, 0, 255),
               thickness,
               line_type)

def main():
    # ArUco detector
    dict_ = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50) #<-Словарик меток подгружаем
    params = cv2.aruco.DetectorParameters()#<-параметры детектора подгружаем
    detector = cv2.aruco.ArucoDetector(dict_, params)# создаем детектор

    cap = cv2.VideoCapture(0)  # подключаемся к камере
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open camera index={0}")
    
    while True:
        ok, frame = cap.read() # получаем кадр с камеры
        if not ok:
            print("Frame grab failed")
            break

        corners, ids, rejected = detector.detectMarkers(frame) # детектируем маркер
        print(corners)

        #тут добавим отрисовку точки середины

        if ids is not None and len(ids) > 0:
            cv2.aruco.drawDetectedMarkers(frame, corners, ids)

        cv2.imshow("aruco_detect", frame)

        key = cv2.waitKey(1) & 0xFF
        if key in (27, ord('q')):   # ESC or q
            break

    

if __name__ == "__main__":
    main()